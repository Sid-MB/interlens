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

"""Communication policies: round-robin, direct piping, and mailbox messaging — driven entirely by scripted
participants (no models, no network)."""
from __future__ import annotations

from interlens import Conversation, DirectPipingPolicy, MessagingPolicy, RoundRobinPolicy
from interlens.message import Message
from interlens.participant import Participant


class Probe(Participant):
	"""A scripted participant that records every view it is asked to generate from."""

	def __init__(self, name, replies=None):
		self.name = name
		self.replies = list(replies or [])
		self.views = []

	def generate(self, view, **kwargs):
		self.views.append(view)
		reply = self.replies.pop(0) if self.replies else f"{self.name}-speaks"
		return Message(self.name, reply)


def view_text(view):
	return "\n".join(m["content"] for m in view)


# --- round-robin ------------------------------------------------------------------------------------------

def test_round_robin_policy_matches_default_order():
	a, b, c = Probe("a"), Probe("b"), Probe("c")
	conv = Conversation(participants=(a, b, c), shared_context="go", communication=RoundRobinPolicy())
	conv.run(turns=6)
	assert [m.author for m in conv.transcript][1:] == ["a", "b", "c", "a", "b", "c"]


# --- direct piping ----------------------------------------------------------------------------------------

def test_direct_piping_shows_only_predecessor():
	a, b, c = Probe("a"), Probe("b"), Probe("c")
	conv = Conversation(participants=(a, b, c), shared_context="go",
	                    communication=DirectPipingPolicy())
	conv.run(turns=6)
	# c's views must contain b's output but never a's (a is not c's predecessor)
	assert any("b-speaks" in view_text(v) for v in c.views)
	assert not any("a-speaks" in view_text(v) for v in c.views)
	# a (predecessor: c) sees c but not b
	assert any("c-speaks" in view_text(v) for v in a.views[1:])
	assert not any("b-speaks" in view_text(v) for v in a.views)
	# the record still holds everything, in order
	assert [m.author for m in conv.transcript][1:] == ["a", "b", "c", "a", "b", "c"]


def test_direct_piping_two_party_equals_dialogue():
	a, b = Probe("a"), Probe("b")
	conv = Conversation(participants=(a, b), shared_context="go", communication=DirectPipingPolicy())
	conv.run(turns=4)
	assert any("a-speaks" in view_text(v) for v in b.views)
	assert any("b-speaks" in view_text(v) for v in a.views[1:])


# --- messaging --------------------------------------------------------------------------------------------

SEND = '```json\n{"send_message": {"recipient": "%s", "content": "%s", "priority": "%s"}}\n```'
READ = '```json\n{"read_message": {}}\n```'


def test_messaging_routing_ping_and_delivery():
	a = Probe("a", replies=["hello. " + SEND % ("b", "secret-for-b", "normal"), "done-a", "done-a2"])
	b = Probe("b", replies=["working", READ, "acting on it", "done-b"])
	c = Probe("c")
	policy = MessagingPolicy()
	conv = Conversation(participants=(a, b, c), shared_context="go", communication=policy)
	conv.run(turns=9)

	# routing: the mail landed in b's box and nowhere else
	assert policy.mailboxes["b"][0].content == "secret-for-b"
	assert "a" not in policy.mailboxes and "c" not in policy.mailboxes
	# ping: after the send, b saw an unread notice before reading
	assert any("unread message" in view_text(v) for v in b.views)
	# delivery: after the read, the content appears in b's view
	assert any("secret-for-b" in view_text(v) for v in b.views)
	# no cross-recipient leakage: c (and a's later views) never see the content or b's turns
	assert not any("secret-for-b" in view_text(v) for v in c.views)
	# autonomy: agents never see each other's raw turns
	assert not any("working" in view_text(v) for v in a.views)
	# first-class events: the send and the read are on the transcript messages + the event log
	sends = [m for m in conv.transcript if m.metadata.get("comm_sends")]
	reads = [m for m in conv.transcript if m.metadata.get("comm_read")]
	assert sends and sends[0].author == "a"
	assert reads and reads[0].author == "b" and reads[0].metadata["comm_read"][0]["content"] == "secret-for-b"
	assert [e["event"] for e in policy.events][:2] == ["send", "read"]


def test_messaging_priority_orders_scheduler_and_delivery():
	# a sends b a normal message then c a high-priority one; c must be scheduled before b,
	# and when one reader holds both priorities, high renders first.
	a = Probe("a", replies=["x. " + SEND % ("b", "low-note", "normal") + "\n" + SEND % ("c", "urgent-note", "high")])
	b = Probe("b", replies=[READ, "b-done"])
	c = Probe("c", replies=[READ, "c-done"])
	policy = MessagingPolicy()
	conv = Conversation(participants=(a, b, c), shared_context="go", communication=policy)
	conv.run(turns=6)
	authors = [m.author for m in conv.transcript][1:]
	assert authors[0] == "a"
	assert authors.index("c") < authors.index("b")  # high-priority ping wins the floor

	# delivery ordering within one reader's box
	policy2 = MessagingPolicy()
	policy2.send("x", "r", "second", "normal")
	policy2.send("x", "r", "first", "high")
	delivered = policy2.read("r")
	assert [m.content for m in delivered] == ["first", "second"]


def test_messaging_fairness_tick_prevents_starvation():
	# a keeps pinging b every turn; the fairness tick must still grant c a turn.
	a = Probe("a", replies=[SEND % ("b", f"m{i}", "normal") for i in range(10)])
	b = Probe("b")
	c = Probe("c")
	policy = MessagingPolicy(fairness_every=2)
	conv = Conversation(participants=(a, b, c), shared_context="go", communication=policy)
	conv.run(turns=12)
	assert any(m.author == "c" for m in conv.transcript)


def test_messaging_read_filter_and_mailbox_persistence():
	policy = MessagingPolicy()
	policy.send("a", "r", "from-a", "normal")
	policy.send("b", "r", "from-b", "normal")
	delivered = policy.read("r", sender="a")
	assert [m.content for m in delivered] == ["from-a"]
	assert [m.content for m in policy.unread("r")] == ["from-b"]  # unrelated mail stays unread
	# events serialize (mailbox persistence path)
	import json
	assert json.loads(json.dumps(policy.events))[0]["event"] == "send"


def test_native_tools_share_the_same_mailboxes():
	policy = MessagingPolicy()
	send_tool, read_tool = policy.tools_for("a")
	send_b, read_b = policy.tools_for("b")
	assert "sent to b" in send_tool(content="via-tool", recipient="b", priority="high")
	assert policy.mailboxes["b"][0].priority == "high"
	assert "via-tool" in read_b()
	assert read_b() == "(no unread messages)"
	assert send_tool.schema["function"]["name"] == "send_message"


def test_policy_state_is_copied_on_branch():
	a, b = Probe("a", replies=[SEND % ("b", "note", "normal")]), Probe("b")
	policy = MessagingPolicy()
	conv = Conversation(participants=(a, b), shared_context="go", communication=policy)
	conv.run(turns=1)
	branch = conv.branch()
	assert branch.communication is not conv.communication
	branch.communication.send("x", "b", "branch-only", "normal")
	assert len(conv.communication.mailboxes["b"]) == 1  # the original is untouched
