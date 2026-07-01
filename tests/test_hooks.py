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
