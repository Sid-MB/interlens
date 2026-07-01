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

"""Serialization round-trips that need no weights: transcript, template (configs/policies/enums), API config."""
from __future__ import annotations

import json

from interlens import (
	Transcript, ContextItem, ConversationTemplate, ModelParticipantConfig, APIParticipantConfig,
	SlidingWindowPolicy, SummarizePolicy, ReasoningVisibility, ExecutionMode,
)
from interlens.participant.config import participant_config_from_dict


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


def test_model_config_round_trip():
	cfg = ModelParticipantConfig(
		name="alice", model="qwen2.5-0.5b", system_prompt="argue A",
		private_context=(ContextItem("secret"),), thinking=False, tool_names=("calc",),
		kv_reuse=True, attn="sdpa", revision="abc123",
	)
	cfg2 = ModelParticipantConfig.from_dict(cfg.to_dict())
	assert cfg2.model == "qwen2.5-0.5b" and cfg2.thinking is False
	assert cfg2.private_context[0].content == "secret"
	assert cfg2.tool_names == ("calc",) and cfg2.kv_reuse is True
	assert cfg2.attn == "sdpa" and cfg2.revision == "abc123"


def test_api_config_polymorphic_dispatch():
	cfg = APIParticipantConfig(name="judge", model_id="claude-x", temperature=0.3)
	cfg2 = participant_config_from_dict(cfg.to_dict())
	assert isinstance(cfg2, APIParticipantConfig)
	assert cfg2.model_id == "claude-x" and cfg2.temperature == 0.3


def test_template_round_trip(tmp_path):
	tmpl = ConversationTemplate(
		participants=[
			ModelParticipantConfig(name="alice", model="qwen2.5-0.5b"),
			ModelParticipantConfig(name="bob", model="gemma2-2b", generation="gemma2"),
		],
		shared_context="Debate.", shared_system_prompt="Brief.",
		context_policy=SlidingWindowPolicy(keep_last=6),
		reasoning_visibility=ReasoningVisibility.SHARED,
		execution_mode=ExecutionMode.DETERMINISTIC,
	)
	path = tmp_path / "tmpl.json"
	tmpl.save(path)
	loaded = ConversationTemplate.load(path)
	assert [c.name for c in loaded.participants] == ["alice", "bob"]
	assert loaded.participants[1].generation == "gemma2"
	assert isinstance(loaded.context_policy, SlidingWindowPolicy) and loaded.context_policy.keep_last == 6
	assert loaded.reasoning_visibility == ReasoningVisibility.SHARED
	assert loaded.execution_mode == ExecutionMode.DETERMINISTIC


def test_summarize_policy_round_trip_drops_callable():
	tmpl = ConversationTemplate(participants=[], context_policy=SummarizePolicy(keep_last=3, summarizer=lambda t: "x"))
	loaded = ConversationTemplate.from_dict(tmpl.to_dict())
	assert isinstance(loaded.context_policy, SummarizePolicy)
	assert loaded.context_policy.keep_last == 3 and loaded.context_policy.summarizer is None


def test_message_hooks_not_in_template():
	assert "message_hooks" not in ConversationTemplate(participants=[]).to_dict()
