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

# interlens: tests for the ScriptedParticipant (a reliable, non-model adversary/pusher).
import pytest

from interlens import Conversation, ScriptedParticipant


def test_cycles_scripts_in_order():
    sp = ScriptedParticipant("alice", ["one", "two", "three"])
    got = [sp.generate([]).content for _ in range(4)]
    assert got == ["one", "two", "three", "one"]   # wraps around


def test_single_string_becomes_one_element_list():
    sp = ScriptedParticipant("alice", "only")
    assert [sp.generate([]).content for _ in range(3)] == ["only", "only", "only"]


def test_empty_scripts_rejected():
    with pytest.raises(ValueError):
        ScriptedParticipant("alice", [])


def test_interp_requests_raise():
    sp = ScriptedParticipant("alice", ["x"])
    for kwargs in ({"steering": object()}, {"capture": object()}, {"patch": object()}, {"return_logprobs": True}):
        with pytest.raises(NotImplementedError):
            sp.generate([], **kwargs)


def test_message_author_is_the_participant_name():
    sp = ScriptedParticipant("pusher", ["hi"])
    assert sp.generate([]).author == "pusher"


def test_runs_in_a_conversation_and_ignores_the_view():
    # Two scripted participants: their turns must land in the transcript verbatim, regardless of what the other
    # said (the scripted replies do not depend on the view).
    a = ScriptedParticipant("alice", ["the answer is 7", "still 7"])
    b = ScriptedParticipant("bob", ["I disagree, it is 5"])
    conv = Conversation((a, b))
    conv.run(turns=3, first="alice")
    spoken = [(m.author, m.content) for m in conv.transcript if m.author != "moderator"]
    assert spoken == [("alice", "the answer is 7"), ("bob", "I disagree, it is 5"), ("alice", "still 7")]
