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
	TurnStopCondition, TokenStopCondition, StopStringCondition, AnyStopCondition,
)
from interlens.message import Message
from .conftest import StubParticipant


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
