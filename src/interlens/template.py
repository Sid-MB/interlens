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

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .conversation import Conversation
from .transcript import Transcript, SCHEMA_VERSION
from .reasoning_visibility import ReasoningVisibility
from .execution_mode import ExecutionMode
from .context import ContextPolicy, ErrorPolicy, context_policy_from_dict
from .participant.config import ParticipantConfig, participant_config_from_dict


@dataclass
class ConversationTemplate:
	"""A reusable, serializable *recipe* for a conversation (serialization level 2): the participant specs plus
	the shared scenario framing and policies, but **no messages**.

	``build`` re-instantiates it into a live ``Conversation`` on given device(s), loading each participant's
	model. This is what lets one scenario be run many times (rollouts) or shipped to worker processes.
	"""

	participants: list[ParticipantConfig]
	shared_context: str | None = None
	shared_system_prompt: str | None = None
	moderator_name: str = "moderator"
	turns: int | None = None
	context_policy: ContextPolicy = field(default_factory=ErrorPolicy)
	context_limit: int | None = None
	reasoning_visibility: ReasoningVisibility = ReasoningVisibility.STRIP
	execution_mode: ExecutionMode = ExecutionMode.THROUGHPUT

	def build(self, devices="cuda", registry=None, transcript: Transcript | None = None) -> Conversation:
		"""Instantiate a live ``Conversation``. ``devices`` may be a single device or a list (participants are
		round-robined across it). ``registry`` resolves tool names (default: process-global). A supplied
		``transcript`` (used by load) is attached as-is, so an already-seeded transcript is not re-seeded."""
		devs = [devices] if isinstance(devices, (str,)) else list(devices)
		participants = tuple(cfg.build(devs[i % len(devs)], registry=registry) for i, cfg in enumerate(self.participants))
		return Conversation(
			participants=participants,
			transcript=transcript if transcript is not None else Transcript(),
			shared_context=self.shared_context,
			shared_system_prompt=self.shared_system_prompt,
			moderator_name=self.moderator_name,
			context_policy=self.context_policy,
			context_limit=self.context_limit,
			reasoning_visibility=self.reasoning_visibility,
			execution_mode=self.execution_mode,
		)

	# --- serialization -------------------------------------------------------------------------------------

	def to_dict(self) -> dict:
		return {
			"schema_version": SCHEMA_VERSION,
			"participants": [c.to_dict() for c in self.participants],
			"shared_context": self.shared_context,
			"shared_system_prompt": self.shared_system_prompt,
			"moderator_name": self.moderator_name,
			"turns": self.turns,
			"context_policy": self.context_policy.to_dict(),
			"context_limit": self.context_limit,
			"reasoning_visibility": self.reasoning_visibility.value,
			"execution_mode": self.execution_mode.value,
		}

	@classmethod
	def from_dict(cls, data: dict) -> "ConversationTemplate":
		return cls(
			participants=[participant_config_from_dict(c) for c in data["participants"]],
			shared_context=data.get("shared_context"),
			shared_system_prompt=data.get("shared_system_prompt"),
			moderator_name=data.get("moderator_name", "moderator"),
			turns=data.get("turns"),
			context_policy=context_policy_from_dict(data["context_policy"]) if data.get("context_policy") else ErrorPolicy(),
			context_limit=data.get("context_limit"),
			reasoning_visibility=ReasoningVisibility(data.get("reasoning_visibility", "strip")),
			execution_mode=ExecutionMode(data.get("execution_mode", "throughput")),
		)

	def save(self, path: str | Path) -> None:
		Path(path).write_text(json.dumps(self.to_dict(), indent=2))

	@classmethod
	def load(cls, path: str | Path) -> "ConversationTemplate":
		return cls.from_dict(json.loads(Path(path).read_text()))
