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

"""Stop conditions: turn/token/string, any-of-list, reset."""
from __future__ import annotations

from interlens import Conversation
from interlens.stop import (
	TurnStopCondition, TokenStopCondition, StopStringCondition, AnyStopCondition, TokenBudget,
)
from interlens.message import Message
from .conftest import StubParticipant


class Budgeted(StubParticipant):
	"""A stub that honors a passed ``max_new_tokens`` cap and records it as ``n_tokens`` — enough to exercise
	``TokenBudget``'s per-turn cap + per-conversation stop without a real model."""

	max_new_tokens = 100

	def generate(self, view, *, max_new_tokens=None, **kw):
		n = max_new_tokens if max_new_tokens is not None else self.max_new_tokens
		return Message(self.name, "x", {"n_tokens": n})


def test_turn_stop_condition():
	conv = Conversation((StubParticipant("a"), StubParticipant("b")))
	conv.run(until=TurnStopCondition(3))
	assert len(conv.transcript) == 3


def test_turn_stop_condition_reset():
	cond = TurnStopCondition(3)
	cond.count = 99
	cond.reset()
	assert cond.count == 0


def test_stop_string_stops_on_generated_content():
	class Done(StubParticipant):
		def generate(self, view, **kw):
			return Message(self.name, "I am DONE")
	conv = Conversation((Done("x"), Done("y")))
	conv.run(turns=10, until=StopStringCondition("DONE"))
	assert len(conv.transcript) == 1


def test_token_stop_condition_accumulates():
	class Toky(StubParticipant):
		def generate(self, view, **kw):
			return Message(self.name, "x", {"n_tokens": 4})
	conv = Conversation((Toky("a"), Toky("b")))
	conv.run(turns=10, until=TokenStopCondition(10))
	assert len(conv.transcript) == 3   # 4 + 4 + 4 = 12 >= 10 on the 3rd turn


def test_any_of_list_stops_on_first():
	conv = Conversation((StubParticipant("a"), StubParticipant("b")))
	conv.run(turns=10, until=[TurnStopCondition(2), StopStringCondition("never")])
	assert len(conv.transcript) == 2


def test_token_budget_caps_per_turn_and_stops_on_budget():
	# per_turn=4 spreads a per_conversation=10 budget across turns: 4 + 4 + 2 = 10 (3rd turn shrunk to land exact).
	conv = Conversation((Budgeted("a"), Budgeted("b")))
	conv.run(turns=100, until=TokenBudget(per_conversation=10, per_turn=4))
	tokens = [m.metadata.get("n_tokens") for m in conv.transcript]
	assert tokens == [4, 4, 2] and sum(tokens) == 10


def test_token_budget_is_per_conversation_not_pooled():
	# Stateless: the same instance judges each conversation by ITS OWN transcript (so a rollout of N copies each
	# gets the full budget, never a shared pool).
	budget = TokenBudget(per_conversation=8)
	full = Conversation((Budgeted("a"),)); full.transcript.append("a", "x", n_tokens=10)
	empty = Conversation((Budgeted("a"),)); empty.transcript.append("a", "x", n_tokens=2)
	assert budget.should_stop(full, full.transcript[-1]) is True
	assert budget.should_stop(empty, empty.transcript[-1]) is False


def test_token_budget_ambient_context_manager():
	conv = Conversation((Budgeted("a"), Budgeted("b")))
	with TokenBudget(per_conversation=8, per_turn=4):
		conv.run(turns=100)
	assert sum(m.metadata.get("n_tokens") for m in conv.transcript) == 8   # 4 + 4
