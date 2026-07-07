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

import contextvars
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..conversation import Conversation
	from ..message import Message

# Ambient stack of conditions installed via ``with condition:`` — a ContextVar so it is coroutine/thread-local and
# never leaks across the process boundary (spawn workers get a fresh, empty stack; rollout/run resolve the stack
# at call time and attach the conditions to each job instead — see ``Conversation.rollout``).
_ambient: contextvars.ContextVar[tuple] = contextvars.ContextVar("interlens_stop_ambient", default=())


def active_stop_conditions() -> tuple["StopCondition", ...]:
	"""The stop conditions currently installed by enclosing ``with condition:`` blocks (outermost first)."""
	return _ambient.get()


class StopCondition(ABC):
	"""A stateful predicate that ends a ``Conversation.run`` early.

	Each condition is **stateful** (tracks its own counters) and is checked after every committed turn via
	``should_stop(conversation, last_message)``. ``reset()`` clears state and is called at the start of each
	``run`` (and branches get fresh copies), so one instance can be reused across runs without leaking state.

	A condition may also **cap the next generation** via ``turn_cap`` (e.g. a token budget shrinks the last turn so
	it lands exactly on budget) and may be installed **ambiently** as a context manager (``with TokenBudget(...):
	conv.rollout(...)`` applies it to every conversation in the block). New conditions subclass this without any
	change to ``run``.
	"""

	@abstractmethod
	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		...

	def reset(self) -> None:
		"""Clear any accumulated state. Default no-op for stateless conditions."""

	def turn_cap(self, conversation: "Conversation") -> int | None:
		"""An upper bound on the NEXT turn's generated tokens, or ``None`` for no cap. The run loop passes it as
		``max_new_tokens`` (bounded by the speaker's own cap), so a budget condition can prevent both overshoot and a
		single turn from consuming the whole allowance. Default: no cap."""
		return None

	def __enter__(self) -> "StopCondition":
		self._ambient_token = _ambient.set(_ambient.get() + (self,))
		return self

	def __exit__(self, *exc) -> None:
		_ambient.reset(self._ambient_token)


class AnyStopCondition(StopCondition):
	"""Fires when *any* member condition fires. ``run(until=[...])`` wraps a list in this."""

	def __init__(self, conditions: list[StopCondition]):
		self.conditions = list(conditions)

	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		# Evaluate all (not short-circuit) so every stateful member sees every turn and updates its counters.
		return any([c.should_stop(conversation, last_message) for c in self.conditions])

	def turn_cap(self, conversation: "Conversation") -> int | None:
		caps = [c.turn_cap(conversation) for c in self.conditions]
		caps = [c for c in caps if c is not None]
		return min(caps) if caps else None

	def reset(self) -> None:
		for c in self.conditions:
			c.reset()
