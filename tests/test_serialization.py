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

"""Serialization round-trips that need no weights: transcript, participant recipes (same-type persistence),
conversation save/load, and per-row templating."""
from __future__ import annotations

import json
import pickle

import pytest

from interlens import (
	Transcript, ContextItem, Conversation, APIParticipant, ModelParticipant, ReasoningVisibility, ExecutionMode,
	dataset_field,
)
from interlens.participant.serialize import participant_to_dict, participant_from_dict
from interlens.templating import resolve, has_fields


def test_transcript_round_trip(tmp_path):
	t = Transcript()
	t.append("moderator", "topic?")
	t.append("alice", "answer", parsed_think="hidden", n_tokens=3)
	path = tmp_path / "t.json"
	t.save(path)
	loaded = Transcript.load(path)
	assert [m.author for m in loaded] == ["moderator", "alice"]
	assert loaded[1].content == "answer" and loaded[1].metadata["parsed_think"] == "hidden"
	assert json.loads(path.read_text())["schema_version"] == 1


def test_model_participant_recipe_round_trip():
	# A lazy participant IS its own recipe: participant_to_dict captures the load spec + settings (no weights).
	p = ModelParticipant(name="alice", hf_id="qwen2.5-0.5b", system_prompt="argue A",
	                     private_context=(ContextItem("secret"),), thinking=False, kv_reuse=True,
	                     attn="sdpa", revision="abc123", max_new_tokens=128)
	data = participant_to_dict(p)
	assert data["kind"] == "model" and data["hf_id"] == "qwen2.5-0.5b" and data["thinking"] is False
	assert data["private_context"][0]["content"] == "secret"
	assert data["kv_reuse"] is True and data["attn"] == "sdpa" and data["revision"] == "abc123"


def test_api_participant_recipe_round_trip():
	p = APIParticipant(name="judge", model_id="claude-x", temperature=0.3)
	p2 = participant_from_dict(participant_to_dict(p))
	assert isinstance(p2, APIParticipant)
	assert p2.model_id == "claude-x" and p2.temperature == 0.3


def test_conversation_save_load_recipe(tmp_path):
	# Save/load a conversation with API participants (no weights) — recipe + transcript round-trip.
	conv = Conversation(
		participants=[APIParticipant(name="a", model_id="m"), APIParticipant(name="b", model_id="m")],
		shared_context="Debate.", shared_system_prompt="Brief.",
		reasoning_visibility=ReasoningVisibility.SHARED, execution_mode=ExecutionMode.DETERMINISTIC,
	)
	conv.transcript.append("a", "hi", n_tokens=1)
	conv.save(tmp_path / "conv")
	loaded = Conversation.load(tmp_path / "conv")
	assert [p.name for p in loaded.participants] == ["a", "b"]
	assert loaded.shared_context == "Debate." and loaded.shared_system_prompt == "Brief."
	assert loaded.reasoning_visibility == ReasoningVisibility.SHARED
	assert loaded.execution_mode == ExecutionMode.DETERMINISTIC
	assert [m.content for m in loaded.transcript] == ["Debate.", "hi"]


def test_load_rejects_old_schema(tmp_path):
	d = tmp_path / "old"
	d.mkdir()
	(d / "conversation.json").write_text(json.dumps({"schema_version": 0, "participants": []}))
	Transcript().save(d / "transcript.json")
	with pytest.raises(ValueError, match="no longer supported"):
		Conversation.load(d)


def test_api_participant_pickles_without_client():
	# The live client is dropped on pickle (unpicklable SDK object) and reconstructed lazily.
	p = APIParticipant(name="j", model_id="m", client=lambda **kw: "x")
	p2 = pickle.loads(pickle.dumps(p))
	assert p2.model_id == "m" and p2.client is None


def test_templating_resolve():
	row = {"question": "2+2?", "topic": "math"}
	assert resolve("plain", row) == "plain"
	assert resolve(dataset_field("question"), row) == "2+2?"
	assert resolve(("Q: ", dataset_field("question")), row) == "Q: 2+2?"
	assert resolve(lambda r: r["topic"].upper(), row) == "MATH"
	assert has_fields(("x", dataset_field("question"))) and not has_fields("plain")
