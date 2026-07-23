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

"""Reasoning persistence: providers' reasoning output (Anthropic thinking blocks, OpenAI-compat reasoning
fields, local <think> streams) must land in per-turn records with a three-state provenance marker —
"none" (no reasoning produced), "withheld_or_summarized" (produced but the provider returned a summary,
redaction, or nothing readable), "full" (complete stream recorded verbatim). Mocked provider responses
throughout; no network."""
from __future__ import annotations

from types import SimpleNamespace as NS

from interlens.participant.participants.api_client import (
	REASONING_FULL, REASONING_NONE, REASONING_WITHHELD,
	Completion, anthropic_reasoning, openai_reasoning)


# ---------------------------------------------------------------- provider extraction (mocked blocks) --

def test_anthropic_no_thinking_blocks_is_none():
	blocks = [NS(type="text", text="hello")]
	assert anthropic_reasoning(blocks) == (None, REASONING_NONE)


def test_anthropic_thinking_blocks_are_persisted_and_marked_withheld_or_summarized():
	# current Claude models return SUMMARIZED thinking over the API: text is persisted, marker says so
	blocks = [NS(type="thinking", thinking="Let me check the shard.", signature="sig"),
	          NS(type="text", text="Answer: 4")]
	text, prov = anthropic_reasoning(blocks)
	assert text == "Let me check the shard."
	assert prov == REASONING_WITHHELD


def test_anthropic_redacted_thinking_is_withheld_with_no_text():
	blocks = [NS(type="redacted_thinking", data="opaque"), NS(type="text", text="Answer: 4")]
	assert anthropic_reasoning(blocks) == (None, REASONING_WITHHELD)


def test_openai_compat_reasoning_content_is_full():
	# OpenRouter/DeepSeek-style raw reasoning stream on the message
	msg = NS(content="Answer: 4", reasoning=None, reasoning_content="chain of thought here")
	text, prov = openai_reasoning(msg, NS(completion_tokens_details=None))
	assert text == "chain of thought here"
	assert prov == REASONING_FULL


def test_openai_reasoning_tokens_without_content_is_withheld():
	# OpenAI reasoning models count reasoning tokens but withhold the stream
	msg = {"content": "Answer: 4"}
	usage = {"completion_tokens_details": {"reasoning_tokens": 384}}
	assert openai_reasoning(msg, usage) == (None, REASONING_WITHHELD)


def test_openai_no_reasoning_is_none():
	assert openai_reasoning({"content": "hi"}, {"completion_tokens_details": {"reasoning_tokens": 0}}) \
		== (None, REASONING_NONE)


# ------------------------------------------------------------------- participant metadata (mock client) --

def _api_participant(completion):
	from interlens.participant.participants.api_participant import APIParticipant
	return APIParticipant(name="p", model_id="test-model", client=lambda *a, **k: completion,
	                      max_tokens=64)


def test_api_participant_metadata_carries_reasoning_record():
	c = Completion("Answer: 4", reasoning="summarized thoughts", reasoning_provenance=REASONING_WITHHELD)
	m = _api_participant(c).generate([{"role": "user", "content": "q"}])
	assert m.metadata["reasoning"] == "summarized thoughts"
	assert m.metadata["reasoning_provenance"] == REASONING_WITHHELD


def test_api_participant_metadata_omits_reasoning_when_none_produced():
	m = _api_participant(Completion("Answer: 4")).generate([{"role": "user", "content": "q"}])
	assert "reasoning" not in m.metadata and "reasoning_provenance" not in m.metadata


# ------------------------------------------------------------- episode schema (engine turn records) --

def _play_one_turn(metadata_extra: dict, content: str = "hello ```json\n{\"answer\": 1}\n```"):
	"""Drive one engine turn with a scripted message carrying the given metadata; return the TurnRecord."""
	import asyncio

	from interlens.arena.engine import EpisodePool
	from interlens.arena.scenarios import InfoRelay
	from interlens.message import Message
	from interlens.participant import Participant

	class OneShot(Participant):
		private_context = ()

		def __init__(self):
			self.name = "player"

		def generate(self, view, **kw):
			return Message(author=self.name, content=content,
			               metadata={"n_tokens": 5, "n_tokens_in": 10} | metadata_extra)

	scenario = InfoRelay()
	instance = scenario.generate_instance(0, 1)
	pool = EpisodePool(store=None)
	episode = asyncio.run(pool.run_episode(scenario, instance, "team", OneShot()))
	return episode.turns[0], episode


def test_turn_record_carries_hosted_reasoning_and_provenance():
	turn, episode = _play_one_turn({"reasoning": "provider summary",
	                                "reasoning_provenance": "withheld_or_summarized"})
	assert turn.reasoning == "provider summary"
	assert turn.reasoning_provenance == "withheld_or_summarized"
	# and it flows into the episode JSON (the export surface)
	j = episode.to_json()
	assert j["turns"][0]["reasoning"] == "provider summary"
	assert j["turns"][0]["reasoning_provenance"] == "withheld_or_summarized"


def test_turn_record_marks_local_think_stream_full():
	turn, _ = _play_one_turn({"parsed_think": "step by step", "raw_completion": "x"})
	assert turn.reasoning == "step by step"
	assert turn.reasoning_provenance == "full"


def test_turn_record_defaults_to_none_without_reasoning():
	turn, episode = _play_one_turn({})
	assert turn.reasoning is None
	assert turn.reasoning_provenance == "none"
	assert episode.to_json()["turns"][0]["reasoning_provenance"] == "none"
