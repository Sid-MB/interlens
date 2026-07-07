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


def _generated_tokens(conversation: "Conversation") -> int:
	"""Total generated tokens committed to ``conversation`` so far, summed from each message's recorded
	``metadata['n_tokens']`` — free (no re-tokenization) since generation already records it. Seeded/moderator turns
	have no count and contribute 0."""
	return sum(int(m.metadata.get("n_tokens") or 0) for m in conversation.transcript)


class TokenBudget(StopCondition):
	"""A per-conversation compute budget — the matched-compute primitive for fair solo-vs-pair comparisons.

	``per_conversation`` stops a conversation once ITS OWN cumulative generated tokens reach the budget, and
	``per_turn`` caps each individual turn so the allowance is spread across real conversation turns rather than
	consumed by one monologue. Both are enforced via ``turn_cap`` too: the run loop shrinks the next generation to
	``min(speaker cap, per_turn, per_conversation - spent)``, so the budget is respected without overshoot.

	**The budget is per-conversation, not a shared pool.** Spend is read from the conversation's own transcript
	(``metadata['n_tokens']``), so the condition is stateless — in a rollout of N copies, each copy independently
	gets the full budget. Cheap to count (never re-tokenizes) and trivially picklable, so it works installed
	directly (``run_until=TokenBudget(...)``) or ambiently (``with TokenBudget(per_conversation=200): conv.rollout()``).
	"""

	def __init__(self, per_conversation: int | None = None, per_turn: int | None = None):
		if per_conversation is None and per_turn is None:
			raise ValueError("TokenBudget needs at least one of per_conversation= or per_turn=")
		self.per_conversation = per_conversation
		self.per_turn = per_turn

	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		if self.per_conversation is None:
			return False
		return _generated_tokens(conversation) >= self.per_conversation

	def turn_cap(self, conversation: "Conversation") -> int | None:
		caps = []
		if self.per_turn is not None:
			caps.append(self.per_turn)
		if self.per_conversation is not None:
			caps.append(max(0, self.per_conversation - _generated_tokens(conversation)))
		return min(caps) if caps else None
