from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..conversation import Conversation
	from ..message import Message


class StopCondition(ABC):
	"""A stateful predicate that ends a ``Conversation.run`` early.

	Each condition is **stateful** (tracks its own counters) and is checked after every committed turn via
	``should_stop(conversation, last_message)``. ``reset()`` clears state and is called at the start of each
	``run`` (and branches get fresh copies), so one instance can be reused across runs without leaking state.

	New conditions (consensus, judge-decides, …) subclass this without any change to ``run``.
	"""

	@abstractmethod
	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		...

	def reset(self) -> None:
		"""Clear any accumulated state. Default no-op for stateless conditions."""


class AnyStopCondition(StopCondition):
	"""Fires when *any* member condition fires. ``run(until=[...])`` wraps a list in this."""

	def __init__(self, conditions: list[StopCondition]):
		self.conditions = list(conditions)

	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		# Evaluate all (not short-circuit) so every stateful member sees every turn and updates its counters.
		return any([c.should_stop(conversation, last_message) for c in self.conditions])

	def reset(self) -> None:
		for c in self.conditions:
			c.reset()
