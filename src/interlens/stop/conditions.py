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

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .stop_condition import StopCondition

if TYPE_CHECKING:
	from ..conversation import Conversation
	from ..message import Message

# The concrete conditions are tiny (a handful of lines each) and share one concern, so they live in one module
# rather than one file apiece — the import ceremony would dwarf the classes. Substantive classes still get their
# own files.


class TurnStopCondition(StopCondition):
	"""Stop after ``max_turns`` committed turns."""

	def __init__(self, max_turns: int):
		self.max_turns = max_turns
		self.count = 0

	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		self.count += 1
		return self.count >= self.max_turns

	def reset(self) -> None:
		self.count = 0


class TokenStopCondition(StopCondition):
	"""Stop once the total generated tokens across turns reach ``max_tokens``.

	The per-turn count comes from ``Message.metadata['n_tokens']``, which ``ModelParticipant.generate`` records —
	so the source of truth is defined, not guessed. Turns without a count (e.g. seeded messages) contribute 0.
	"""

	def __init__(self, max_tokens: int):
		self.max_tokens = max_tokens
		self.total = 0

	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		self.total += int(last_message.metadata.get("n_tokens") or 0)
		return self.total >= self.max_tokens

	def reset(self) -> None:
		self.total = 0


class ElapsedTimeStopCondition(StopCondition):
	"""Stop once ``seconds`` of wall-clock have elapsed since the run started (monotonic clock)."""

	def __init__(self, seconds: float):
		self.seconds = seconds
		self.start = None

	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		if self.start is None:
			self.start = time.monotonic()
		return (time.monotonic() - self.start) >= self.seconds

	def reset(self) -> None:
		self.start = None


class StopStringCondition(StopCondition):
	"""Stop when a committed message's visible ``content`` contains any of the given strings (a done-signal)."""

	def __init__(self, strings):
		self.strings = [strings] if isinstance(strings, str) else list(strings)

	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		return any(s in last_message.content for s in self.strings)
