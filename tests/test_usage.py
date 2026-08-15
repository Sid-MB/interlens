# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Usage accounting: meter arithmetic, reservation gating, persistence, refusal telemetry, cost budgets, and
the APIParticipant metadata path (with mocked clients — no network)."""
from __future__ import annotations

import json
import pickle
from types import SimpleNamespace

import pytest

from interlens import (
	APIParticipant, CostBudget, Conversation, OpenRouterRouting, TokenBudget, UsageMeter, transcript_usage,
)
from interlens.participant.participants.api_client import Completion
from interlens.participant.participants.api_participant import PromptCache
from interlens.usage import register_pricing


def test_meter_arithmetic_and_breakdown():
	meter = UsageMeter(pricing={"m": {"in": 10.0, "out": 50.0}})
	cost = meter.add("m", 1_000_000, 1_000_000)
	assert cost == pytest.approx(60.0)
	cost_batch = meter.add("m", 2_000_000, 0, price_multiplier=0.5)
	assert cost_batch == pytest.approx(10.0)
	assert meter.total_usd == pytest.approx(70.0)
	m = meter.by_model["m"]
	assert (m["in"], m["out"], m["calls"]) == (3_000_000, 1_000_000, 2)


def test_unknown_model_uses_conservative_fallback():
	meter = UsageMeter()
	# fallback pricing must be non-zero (never silently free) and high (over- not under-count)
	assert meter.price("never-heard-of-it", 1_000_000, 0) >= 25.0


def test_register_pricing_flows_into_new_meters():
	register_pricing("custom-model-x", input_per_mtok=1.0, output_per_mtok=2.0)
	assert UsageMeter().price("custom-model-x", 1_000_000, 1_000_000) == pytest.approx(3.0)


def test_reservation_gating():
	meter = UsageMeter(budget=10.0, pricing={"m": {"in": 1.0, "out": 1.0}})
	assert meter.reserve(6.0)
	assert not meter.reserve(5.0)      # 6 + 5 > 10: doesn't fit, nothing claimed
	assert meter.reserve(3.0)          # 6 + 3 <= 10
	meter.settle(6.0)
	assert meter.reserved_usd == pytest.approx(3.0)
	meter.add("m", 9_000_000, 0)       # $9 actual spend
	assert not meter.exhausted
	meter.add("m", 1_000_000, 0)
	assert meter.exhausted


def test_meter_persistence_roundtrip(tmp_path):
	path = tmp_path / "spend.json"
	meter = UsageMeter(budget=100.0, path=path, pricing={"m": {"in": 10.0, "out": 10.0}})
	meter.add("m", 1_000_000, 0, refusal=True)
	resumed = UsageMeter(budget=100.0, path=path)
	assert resumed.total_usd == pytest.approx(10.0)
	assert resumed.by_model["m"]["refusals"] == 1
	assert json.loads(path.read_text())["total_usd"] == pytest.approx(10.0)


def test_meter_survives_pickling():
	meter = UsageMeter(budget=5.0, pricing={"m": {"in": 1.0, "out": 1.0}})
	meter.add("m", 1_000_000, 0)
	clone = pickle.loads(pickle.dumps(meter))
	assert clone.total_usd == pytest.approx(1.0)
	clone.add("m", 1_000_000, 0)  # the restored lock works
	assert clone.total_usd == pytest.approx(2.0)


class _UsageClient:
	"""A mocked API client returning Completions with declared usage."""

	def __init__(self, text="ok", tokens_in=100, tokens_out=50, stop_reason="end_turn"):
		self.kw = dict(input_tokens=tokens_in, output_tokens=tokens_out, stop_reason=stop_reason)
		self.text = text
		self.calls = []

	def __call__(self, system, messages, model, max_tokens, temperature):
		self.calls.append({"max_tokens": max_tokens})
		return Completion(self.text, **self.kw)


def test_api_participant_records_usage_and_meters():
	meter = UsageMeter(pricing={"m": {"in": 10.0, "out": 20.0}})
	p = APIParticipant(name="a", model_id="m", client=_UsageClient(), meter=meter)
	msg = p.generate([{"role": "user", "content": "hi"}])
	assert msg.metadata["n_tokens"] == 50
	assert msg.metadata["n_tokens_in"] == 100
	assert msg.metadata["stop_reason"] == "end_turn"
	assert msg.metadata["cost_usd"] == pytest.approx(100 * 10 / 1e6 + 50 * 20 / 1e6)
	assert meter.total_usd == pytest.approx(msg.metadata["cost_usd"])
	assert "refusal" not in msg.metadata


def test_api_participant_refusal_classification():
	meter = UsageMeter()
	p = APIParticipant(name="a", model_id="m", client=_UsageClient(stop_reason="refusal"), meter=meter)
	msg = p.generate([{"role": "user", "content": "hi"}])
	assert msg.metadata["refusal"] is True
	assert meter.by_model["m"]["refusals"] == 1
	# the OpenAI-schema analogue classifies too
	p2 = APIParticipant(name="b", model_id="m", client=_UsageClient(stop_reason="content_filter"))
	assert p2.generate([{"role": "user", "content": "hi"}]).metadata["refusal"] is True


def test_api_participant_tolerates_plain_str_clients():
	# injected test clients that return a bare str (the documented contract) still work; usage reads as 0
	p = APIParticipant(name="a", model_id="m", client=lambda **kw: "plain")
	msg = p.generate([{"role": "user", "content": "hi"}])
	assert msg.content == "plain"
	assert msg.metadata["n_tokens"] == 0


class _OpenRouterProbe:
	def __init__(self, *, served_by="Together"):
		self.served_by = served_by
		self.calls = []

	def __call__(self, **kwargs):
		self.calls.append(kwargs)
		return Completion("ok", upstream_provider=self.served_by,
		                  response_model="meta-llama/llama-3.1-70b-instruct",
		                  generation_id="gen-test")


def test_openrouter_research_routing_is_pinned_and_auditable():
	client = _OpenRouterProbe()
	routing = OpenRouterRouting(
		upstream_provider="together", quantizations=("bf16",), data_collection="deny")
	p = APIParticipant(name="a", provider="openrouter",
	                   model_id="meta-llama/llama-3.1-70b-instruct",
	                   openrouter_routing=routing, client=client)
	msg = p.generate([{"role": "user", "content": "hi"}])
	assert client.calls[0]["provider_routing"] == {
		"order": ["together"], "only": ["together"], "allow_fallbacks": False,
		"require_parameters": True, "quantizations": ["bf16"], "data_collection": "deny"}
	assert msg.metadata["upstream_provider"] == "Together"
	assert msg.metadata["response_model"] == "meta-llama/llama-3.1-70b-instruct"
	assert msg.metadata["generation_id"] == "gen-test"
	assert msg.metadata["provider_routing"] == client.calls[0]["provider_routing"]


def test_openrouter_client_sends_extension_in_extra_body_and_captures_identity():
	from interlens.participant.participants.api_client import OpenRouterClient

	class _Completions:
		def __init__(self):
			self.kwargs = None

		def create(self, **kwargs):
			self.kwargs = kwargs
			message = SimpleNamespace(content="ok")
			choice = SimpleNamespace(message=message, finish_reason="stop")
			usage = SimpleNamespace(prompt_tokens=3, completion_tokens=2, completion_tokens_details=None)
			return SimpleNamespace(
				choices=[choice], usage=usage, provider="Together", model="model/resolved", id="gen-123")

	completions = _Completions()
	client = object.__new__(OpenRouterClient)  # skip real SDK/key initialization
	client._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
	result = client._call_once(
		None, [{"role": "user", "content": "hi"}], "model/requested", 20, 0.2,
		provider_routing={"only": ["together"], "allow_fallbacks": False})
	assert completions.kwargs["extra_body"] == {
		"provider": {"only": ["together"], "allow_fallbacks": False}}
	assert result.upstream_provider == "Together"
	assert result.response_model == "model/resolved"
	assert result.generation_id == "gen-123"


def test_openrouter_uncontrolled_or_inconsistent_routing_fails_loudly():
	no_routing = APIParticipant(
		name="a", provider="openrouter", model_id="m", client=_OpenRouterProbe())
	with pytest.raises(ValueError, match="explicit routing"):
		no_routing.generate([{"role": "user", "content": "hi"}])

	mismatch = APIParticipant(
		name="a", provider="openrouter", model_id="m",
		openrouter_routing=OpenRouterRouting(upstream_provider="together"),
		client=_OpenRouterProbe(served_by="DeepInfra"))
	with pytest.raises(RuntimeError, match="routing violation"):
		mismatch.generate([{"role": "user", "content": "hi"}])

	missing_metadata = APIParticipant(
		name="a", provider="openrouter", model_id="m",
		openrouter_routing=OpenRouterRouting(upstream_provider="together"),
		client=lambda **kwargs: Completion("ok"))
	with pytest.raises(RuntimeError, match="did not report"):
		missing_metadata.generate([{"role": "user", "content": "hi"}])

	# Unpinned routing remains available, but only by explicit opt-out and is still parameter-safe.
	exploratory_client = _OpenRouterProbe(served_by="DeepInfra")
	exploratory = APIParticipant(
		name="a", provider="openrouter", model_id="m",
		openrouter_routing=OpenRouterRouting.unpinned(), client=exploratory_client)
	exploratory.generate([{"role": "user", "content": "hi"}])
	assert exploratory_client.calls[0]["provider_routing"] == {"require_parameters": True}


def test_turn_token_floor_raises_external_caps():
	client = _UsageClient()
	p = APIParticipant(name="a", model_id="m", client=client, turn_token_floor=2048, max_tokens=512)
	p.generate([{"role": "user", "content": "hi"}], max_new_tokens=300)   # a budget-shrunk turn
	p.generate([{"role": "user", "content": "hi"}], max_new_tokens=4096)  # a roomy turn is untouched
	p.generate([{"role": "user", "content": "hi"}])                       # own default, floored
	assert [c["max_tokens"] for c in client.calls] == [2048, 4096, 2048]


def _stub(name, reply, tokens_out, cost):
	from interlens.message import Message
	from interlens.participant import Participant

	class _P(Participant):
		def __init__(self):
			self.name = name

		def generate(self, view, **kw):
			return Message(name, reply, {"n_tokens": tokens_out, "cost_usd": cost})
	return _P()


def test_cost_budget_stops_conversation():
	a, b = _stub("a", "hi", 10, 0.6), _stub("b", "ho", 10, 0.6)
	conv = Conversation(participants=(a, b), shared_context="talk")
	conv.run(turns=10, until=CostBudget(per_conversation=1.5))
	# stops once cumulative recorded cost reaches $1.5 (after the 3rd costed turn)
	assert len([m for m in conv.transcript if m.author in ("a", "b")]) == 3


def test_transcript_usage_aggregation():
	a, b = _stub("a", "hi", 10, 0.25), _stub("b", "ho", 20, 0.5)
	conv = Conversation(participants=(a, b), shared_context="talk")
	conv.run(turns=4, until=TokenBudget(per_conversation=10_000))
	usage = transcript_usage(conv.transcript)
	assert usage["tokens_out"] == 60
	assert usage["cost_usd"] == pytest.approx(1.5)
	assert usage["by_author"]["a"]["turns"] == 2
	assert usage["by_author"]["b"]["tokens_out"] == 40


def test_thinking_control_mapping_and_guards():
	from interlens.participant.participants.api_client import AnthropicClient, _OpenAICompatClient

	map_ = AnthropicClient._thinking_param
	assert map_(None) is None
	assert map_("disabled") == {"type": "disabled"}
	assert map_(4096) == {"type": "enabled", "budget_tokens": 4096}
	assert map_({"type": "enabled", "budget_tokens": 1}) == {"type": "enabled", "budget_tokens": 1}
	with pytest.raises(ValueError):
		map_("sometimes")

	# a thinking-configured participant forwards the value to its client
	class ThinkingProbe(_UsageClient):
		def __call__(self, system, messages, model, max_tokens, temperature, thinking=None):
			self.calls.append({"thinking": thinking})
			return Completion(self.text, **self.kw)

	probe = ThinkingProbe()
	p = APIParticipant(name="a", model_id="m", client=probe, thinking="disabled")
	p.generate([{"role": "user", "content": "hi"}])
	assert probe.calls[-1]["thinking"] == "disabled"

	# non-Anthropic providers must fail loudly on a thinking request (never silently ignore)
	class _FakeOpenAICompat(_OpenAICompatClient):
		def __init__(self):  # skip SDK/env setup
			pass
	with pytest.raises(NotImplementedError):
		_FakeOpenAICompat()._call_once(None, [], "m", 10, None, thinking="disabled")


# --- prompt caching ---------------------------------------------------------------------------------------

class _CacheClient:
	"""A mocked Anthropic client reporting cache usage and capturing the request it was handed."""

	def __init__(self, *, tokens_in=200, cache_read=0, cache_write=0):
		self.kw = dict(input_tokens=tokens_in, output_tokens=10,
		               cache_read_tokens=cache_read, cache_write_tokens=cache_write)
		self.requests = []

	def __call__(self, system, messages, model, max_tokens, temperature, **rest):
		self.requests.append({"system": system, "messages": messages})
		return Completion("ok", **self.kw)


def test_prompt_cache_split_is_byte_preserving_and_marks_only_stable_prefixes():
	spec = PromptCache(marks=("## Prior stages", "## Your private"))
	text = "## Catalogue\nA\n\n## Prior stages\nB\n\n## Your private\nC\n\n## Now\nD"
	blocks = spec.split(text)
	assert "".join(b["text"] for b in blocks) == text     # the seat reads exactly what it read uncached
	assert [("cache_control" in b) for b in blocks] == [True, True, False]  # the volatile tail is never marked


def test_prompt_cache_skips_absent_marks_rather_than_raising():
	# A view legitimately varies by phase, so a heading missing this turn must degrade to fewer breakpoints.
	spec = PromptCache(marks=("## Prior stages", "## Missing"))
	blocks = spec.split("## Catalogue\nA\n\n## Prior stages\nB")
	assert len(blocks) == 2 and "".join(b["text"] for b in blocks).startswith("## Catalogue")


def test_prompt_cache_respects_the_four_breakpoint_ceiling():
	spec = PromptCache(system=True, marks=tuple(f"#{i}" for i in range(1, 7)))
	blocks = spec.split("".join(f"#{i} body " for i in range(7)))
	assert sum("cache_control" in b for b in blocks) == 3   # 4 total minus the system breakpoint


def test_prompt_cache_wires_breakpoints_into_the_request():
	client = _CacheClient()
	p = APIParticipant(name="a", model_id="m", client=client,
	                   prompt_cache=PromptCache(marks=("## Now",), ttl="1h"))
	p.generate([{"role": "system", "content": "framing"}, {"role": "user", "content": "cat\n\n## Now\nbid"}])
	sent = client.requests[0]
	assert sent["system"] == [{"type": "text", "text": "framing",
	                           "cache_control": {"type": "ephemeral", "ttl": "1h"}}]
	assert [("cache_control" in b) for b in sent["messages"][-1]["content"]] == [True, False]


def test_no_prompt_cache_leaves_the_request_untouched():
	client = _CacheClient()
	APIParticipant(name="a", model_id="m", client=client).generate(
		[{"role": "system", "content": "framing"}, {"role": "user", "content": "hi"}])
	assert client.requests[0] == {"system": "framing", "messages": [{"role": "user", "content": "hi"}]}


def test_prompt_cache_is_anthropic_only():
	p = APIParticipant(name="a", model_id="m", provider="openai", client=_CacheClient(),
	                   prompt_cache=PromptCache())
	with pytest.raises(ValueError, match="Anthropic-only"):
		p.generate([{"role": "user", "content": "hi"}])


def test_cached_call_prices_reads_and_writes_off_the_input_rate():
	meter = UsageMeter(pricing={"m": {"in": 10.0, "out": 20.0}})
	p = APIParticipant(name="a", model_id="m", meter=meter, prompt_cache=PromptCache(),
	                   client=_CacheClient(tokens_in=100, cache_read=800, cache_write=100))
	msg = p.generate([{"role": "user", "content": "hi"}])
	assert msg.metadata["cost_usd"] == pytest.approx(
		(100 * 10 + 800 * 10 * 0.1 + 100 * 10 * 1.25) / 1e6 + 10 * 20 / 1e6)
	# the recorded prompt size is the WHOLE prompt, so it stays comparable to an uncached run
	assert msg.metadata["n_tokens_in"] == 1000
	assert msg.metadata["n_tokens_cache_read"] == 800


def test_cache_report_hit_rate_and_a_negative_saving_when_nothing_is_reread():
	meter = UsageMeter(pricing={"m": {"in": 10.0, "out": 20.0}})
	meter.add("m", 100, 10, cache_read_tokens=800, cache_write_tokens=100)
	report = meter.cache_report()["m"]
	assert report["prompt_tokens"] == 1000 and report["hit_rate"] == pytest.approx(0.8)
	assert report["saved_usd"] > 0

	# breakpoints on an unstable prefix: every turn writes, nothing ever reads — this must NOT report 0.
	waste = UsageMeter(pricing={"m": {"in": 10.0, "out": 20.0}})
	waste.add("m", 0, 10, cache_write_tokens=1000)
	assert waste.cache_report()["m"]["saved_usd"] < 0


def test_request_config_records_the_caching_condition():
	p = APIParticipant(name="a", model_id="m", prompt_cache=PromptCache(marks=("## Now",), ttl="1h"))
	assert p.request_config()["prompt_cache"] == {"system": True, "marks": ["## Now"], "ttl": "1h"}
	assert APIParticipant(name="a", model_id="m").request_config()["prompt_cache"] is None
