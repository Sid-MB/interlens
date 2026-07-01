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

"""Message-hook middleware: edit, deny, empty-chain pass-through, branch carry."""
from __future__ import annotations

from interlens import Conversation, MessageHook, MessageHookResult, ConversationTemplate
from interlens.message import Message
from .conftest import StubParticipant


class _UpperEdit(MessageHook):
	def review(self, message, conversation):
		return MessageHookResult.edit(Message(message.author, message.content.upper(), message.metadata))


class _DenyBob(MessageHook):
	def review(self, message, conversation):
		return MessageHookResult.deny() if message.author == "b" else MessageHookResult.approve()


def test_edit_hook_rewrites_committed():
	conv = Conversation((StubParticipant("a"), StubParticipant("b")), message_hooks=[_UpperEdit()])
	conv.run(turns=2)
	assert all(m.content == m.content.upper() for m in conv.transcript)


def test_deny_hook_drops_turns():
	conv = Conversation((StubParticipant("a"), StubParticipant("b")), message_hooks=[_DenyBob()])
	conv.run(turns=4)
	assert [m.author for m in conv.transcript] == ["a", "a"]  # every bob turn denied, nothing committed


def test_empty_chain_is_pass_through():
	conv = Conversation((StubParticipant("a"), StubParticipant("b")))
	conv.run(turns=2)
	assert [m.content for m in conv.transcript] == ["a-says", "b-says"]


def test_hooks_carried_by_branch():
	conv = Conversation((StubParticipant("a"), StubParticipant("b")), message_hooks=[_UpperEdit()])
	branch = conv.branch()
	assert len(branch.message_hooks) == 1
