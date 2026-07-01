# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Real-model tests (opt-in): loads a small Qwen. Deselected by default; run with:

    uv run pytest tests/test_models_slow.py -m slow

Uses mps if available, else cpu, greedy + short generations. On a GPU box these also cover the paths that
can't be exercised on a Mac (they'll pick up cuda automatically via the device fixture).
"""
from __future__ import annotations

import pytest
import torch

pytestmark = pytest.mark.slow

MODEL = "qwen2.5-0.5b"


@pytest.fixture(scope="module")
def device():
	if torch.cuda.is_available():
		return "cuda"
	if torch.backends.mps.is_available():
		return "mps"
	return "cpu"


def _conv(device, **kw):
	from interlens import Conversation
	return Conversation.from_models((MODEL, MODEL), names=("alice", "bob"), device=device,
	                                dtype=torch.float32, temperature=0.0, max_new_tokens=16, **kw)


def test_two_models_talk_and_share_weights(device):
	conv = _conv(device)
	assert conv.by_name["alice"].model is conv.by_name["bob"].model   # same id -> one load
	conv.transcript.append("bob", "Name one color.")
	conv.run(turns=2, first="alice")   # first-by-name
	assert [m.author for m in conv.transcript] == ["bob", "alice", "bob"]
	assert all(m.content.strip() for m in conv.transcript)


def test_auto_from_model_infers_tokenizer_and_family(device):
	"""AutoModelParticipant.from_model / from_ on a bare PreTrainedModel infers the tokenizer and family class."""
	from interlens import AutoModelParticipant
	from interlens.loading import load_model
	model, _tok = load_model(MODEL, device=device, dtype=torch.float32)

	p = AutoModelParticipant.from_model(model, name="p")           # no tokenizer passed
	assert p.tokenizer is not None
	assert type(p).__name__ == "QwenModelParticipant"              # family inferred from the model's HF id

	p2 = AutoModelParticipant.from_(model, name="p2")             # from_ dispatches PreTrainedModel -> from_model
	assert type(p2).__name__ == "QwenModelParticipant" and p2.tokenizer is not None


def test_shared_scenario_pipeline_and_save_load(device, tmp_path):
	from interlens import ConversationTemplate, ModelParticipantConfig, Conversation
	tmpl = ConversationTemplate(
		participants=[ModelParticipantConfig(name="a", model=MODEL, dtype="float32", temperature=0.0,
		                                     max_new_tokens=12, system_prompt="Be terse."),
		              ModelParticipantConfig(name="b", model=MODEL, dtype="float32", temperature=0.0,
		                                     max_new_tokens=12, system_prompt="Be terse.")],
		shared_context="Is the moon larger than Australia's width?",
	)
	conv = tmpl.build(devices=device)
	view = conv._view(conv.by_name["a"])
	assert view[0]["role"] == "system" and "terse" in view[0]["content"].lower()
	conv.run(turns=2, first=conv.by_name["a"])
	conv.save(tmp_path / "run")
	loaded = Conversation.load(tmp_path / "run", devices=device)
	assert [m.content for m in loaded.transcript] == [m.content for m in conv.transcript]


def test_interp_capture_and_steering(device):
	from interlens import SteeringSpec
	from interlens.interp import decoder_layers
	conv = _conv(device)
	conv.transcript.append("bob", "Say one short sentence about the sky.")
	model = conv.by_name["alice"].model
	d_model = model.config.hidden_size

	with conv.capture(sites=["residual"], layers=[4]) as cache:
		conv.step(conv.by_name["alice"])
	rec = cache.query(participant="alice", layer=4)[0]
	assert rec.tensor.ndim == 2 and rec.tensor.shape[1] == d_model
	assert "answer" in rec.phases

	base = conv.sample("alice", "Reply in one word.")
	direction = torch.randn(d_model)
	steered = conv.sample("alice", "Reply in one word.",
	                      steering=SteeringSpec(direction=direction, layers=(6,), coef=14.0, mode="add"))
	assert steered.metadata["steering"]["mode"] == "add"
	assert base.content != steered.content   # strong steering perturbs greedy output


def test_generate_batch_shapes_and_shared_prefill(device):
	"""Batched generate returns one Message per view; identical prompts take the shared-prefill fast path."""
	from interlens import Conversation
	conv = Conversation.from_models((MODEL, MODEL), names=("alice", "bob"), device=device,
	                                dtype=torch.float32, temperature=0.8, max_new_tokens=12)
	conv.transcript.append("bob", "Say one word about the weather.")
	alice = conv.by_name["alice"]
	same_view = conv._view(alice)
	msgs = alice.generate_batch([same_view, same_view, same_view], group_seed=0)
	assert len(msgs) == 3
	assert all(m.author == "alice" and m.metadata["batched"] for m in msgs)
	assert all(m.metadata["shared_prefill"] for m in msgs)   # identical prompts -> one prefill, N samples

	# Differing prompts -> left-padded batch path (no shared prefill), still one Message per view.
	v2 = conv._view(conv.by_name["bob"])
	mixed = alice.generate_batch([same_view, v2], group_seed=1)
	assert len(mixed) == 2 and not any(m.metadata["shared_prefill"] for m in mixed)


def test_batched_rollout_costeps_and_saves(device, tmp_path):
	"""Batched rollout co-steps all conversations, produces the right shape, and checkpoints each — asserted
	distributionally (every conv fills its turns), NOT token-identical to unbatched (PLAN §Execution modes)."""
	from interlens import ConversationTemplate, ModelParticipantConfig, rollout
	tmpl = ConversationTemplate(
		participants=[ModelParticipantConfig(name="a", model=MODEL, dtype="float32", temperature=0.8,
		                                     max_new_tokens=12, system_prompt="Argue YES, briefly."),
		              ModelParticipantConfig(name="b", model=MODEL, dtype="float32", temperature=0.8,
		                                     max_new_tokens=12, system_prompt="Argue NO, briefly.")],
		shared_context="Is cereal a soup?", turns=4)
	report = rollout(tmpl, n=4, devices=[device], out_dir=tmp_path / "b", batched=True, max_batch_size=2)
	assert not report.failed and len(report.results) == 4
	for r in report.results.values():
		assert len(r.transcript) == 5                       # 4 co-stepped turns + the moderator seed
		assert any(m.metadata.get("batched") for m in r.transcript)
		assert (tmp_path / "b" / r.job_id / "transcript.json").exists()


def test_kv_reuse_output_equivalence(device):
	def run(kv):
		conv = _conv(device, kv_reuse=kv)
		conv.transcript.append("b", "Name one color.")
		conv.run(turns=3, first=conv.by_name["alice"])
		return [m.content for m in conv.transcript]
	assert run(False) == run(True)   # guarded reuse must not change greedy output
