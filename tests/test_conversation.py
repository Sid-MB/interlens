"""Core loop: role-swap rendering, scenario framing privacy, branch isolation, ephemeral sampling."""
from __future__ import annotations

import pytest

from interlens import Conversation, ContextItem
from interlens.message import Message
from .conftest import StubParticipant


def test_alternation_and_role_swap():
	a, b = StubParticipant("alice"), StubParticipant("bob")
	conv = Conversation((a, b))
	conv.run(turns=4)
	assert [m.author for m in conv.transcript] == ["alice", "bob", "alice", "bob"]

	va = conv.transcript.render_roles(pov=a)
	vb = conv.transcript.render_roles(pov=b)
	assert [m["role"] for m in va] == ["assistant", "user", "assistant", "user"]
	assert [m["role"] for m in vb] == ["user", "assistant", "user", "assistant"]
	# Same content between views; only roles differ.
	assert [m["content"] for m in va] == [m["content"] for m in vb]


def test_duplicate_names_rejected():
	with pytest.raises(ValueError):
		Conversation((StubParticipant("x"), StubParticipant("x")))


def test_moderator_name_collision_rejected():
	with pytest.raises(ValueError):
		Conversation((StubParticipant("moderator"), StubParticipant("b")), shared_context="hi")


def test_with_extra_does_not_mutate_and_shares_messages():
	a, b = StubParticipant("alice"), StubParticipant("bob")
	conv = Conversation((a, b))
	conv.run(turns=2)
	n = len(conv.transcript)
	extended = conv.transcript.with_extra(Message("bob", "ephemeral"))
	assert len(extended) == n + 1
	assert len(conv.transcript) == n                       # original untouched
	assert extended[0] is conv.transcript[0]               # Message objects shared, not copied
	assert extended[-1].content == "ephemeral"
	assert extended.messages._base is conv.transcript.messages   # base list referenced, NOT copied
	# renders like a normal transcript from a POV
	assert [m["content"] for m in extended.render_roles(pov=a)][-1] == "ephemeral"
	# it's a read-only ephemeral view: appending raises rather than silently diverging
	with pytest.raises(TypeError):
		extended.append("bob", "nope")


def test_scenario_framing_privacy():
	alice = StubParticipant("alice", system_prompt="You secretly argue HARMFUL.",
	                        private_context=(ContextItem("SECRET fact"),))
	bob = StubParticipant("bob", system_prompt="You secretly argue POSITIVE.")
	conv = Conversation((alice, bob), shared_context="Debate topic?", shared_system_prompt="Be concise.")

	# shared_context seeded as a moderator turn.
	assert conv.transcript[0].author == "moderator"

	va = conv._view(alice)
	assert va[0]["role"] == "system"
	assert "HARMFUL" in va[0]["content"] and "Be concise." in va[0]["content"]
	assert "POSITIVE" not in va[0]["content"]               # bob's secret never leaks to alice
	assert any("SECRET fact" in m["content"] for m in va)   # alice sees her own private context

	vb = conv._view(bob)
	assert not any("SECRET" in m["content"] for m in vb)
	assert "HARMFUL" not in "".join(m["content"] for m in vb)

	# The shared transcript holds neither secret nor private context.
	assert all("SECRET" not in m.content and "HARMFUL" not in m.content for m in conv.transcript)


def test_branch_isolation_shares_participants():
	base = Conversation((StubParticipant("a"), StubParticipant("b")))
	base.run(turns=2)
	branch = base.branch()
	branch.run(turns=2)
	assert len(base.transcript) == 2 and len(branch.transcript) == 4  # base frozen, branch diverged
	assert branch.by_name["a"] is base.by_name["a"]                   # participants shared, no reload


def test_sample_is_ephemeral():
	a, b = StubParticipant("alice", reply="ans"), StubParticipant("bob")
	conv = Conversation((a, b))
	conv.run(turns=2)
	n = len(conv.transcript)
	msg = conv.sample("alice", "what do you think?")
	assert msg.author == "alice" and len(conv.transcript) == n
	# The injected message is attributed to the other participant and rendered as an incoming turn.
	assert any("what do you think?" == m["content"] for m in a.last_view)
