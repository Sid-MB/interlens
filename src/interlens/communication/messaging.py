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

"""Tool-mediated asynchronous messaging between autonomous agents.

Under ``MessagingPolicy`` there is **no shared conversation**: each agent sees only the moderator framing and
its own past turns. Communication is explicit — an agent *sends* a message to a named recipient
(``send_message``: content, ``normal``/``high`` priority), the recipient gets a **ping** (a lightweight notice
in its next view: how many unread, from whom, at what priority), and *reads* its mailbox (``read_message``),
after which the mail is delivered into its view. The activation scheduler grants turns ping-first (high
priority ahead of normal), with a **fairness tick** so agents nobody has pinged still act regularly, and lets a
reader act on freshly delivered mail immediately.

Both invocation surfaces feed the same mailboxes:

- **Fenced-JSON actions** (family-agnostic, works for every participant type — API, local, scripted): an agent
  ends its turn with ``{"send_message": {"recipient": ..., "content": ..., "priority": ...}}`` or
  ``{"read_message": {}}``; the policy parses committed turns in ``on_commit``.
- **Native tools** (local model participants with a tool-calling family): ``policy.tools_for(name)`` returns
  ``Tool`` objects to attach via ``tools=`` — ``read_message`` then resolves *within* the turn (the model reads
  and reacts in one generation), and the call/result trail lands in ``metadata['tool_trail']`` as usual.

Everything is recorded first-class for scoring and replay: each send/read/delivery appends a structured event
to ``policy.events`` (JSON-serializable) *and* annotates the committed message's metadata
(``comm_sends`` / ``comm_read``), so a saved transcript carries the full message traffic.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .policy import CommunicationPolicy
from ..tools.tool import Tool
from ..view import ViewSegment

if TYPE_CHECKING:
	from ..conversation import Conversation
	from ..message import Message
	from ..participant import Participant

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

PRIORITIES = ("normal", "high")


def parse_json_actions(text: str) -> list[dict]:
	"""All fenced JSON objects in ``text``, parsed (malformed fences are skipped, not fatal)."""
	out = []
	for candidate in _FENCE.findall(text or ""):
		try:
			obj = json.loads(candidate)
		except json.JSONDecodeError:
			continue
		if isinstance(obj, dict):
			out.append(obj)
	return out


@dataclass
class Mail:
	"""One mailbox item. ``read`` flips when the recipient reads; delivered mail renders into its views."""
	sender: str
	recipient: str
	content: str
	priority: str = "normal"
	sent_at_turn: int = 0
	read: bool = False

	def to_dict(self) -> dict:
		return {"sender": self.sender, "recipient": self.recipient, "content": self.content,
		        "priority": self.priority, "sent_at_turn": self.sent_at_turn, "read": self.read}


class SendMessageTool(Tool):
	"""Native-tool surface for sending: ``send_message(content, recipient, priority)``. Bound to one sender."""

	name = "send_message"

	def __init__(self, policy: "MessagingPolicy", sender: str):
		self._policy = policy
		self._sender = sender

	@property
	def schema(self) -> dict:
		return {"type": "function", "function": {
			"name": "send_message",
			"description": "Send a private message to another agent. They are notified and can read it.",
			"parameters": {"type": "object", "properties": {
				"content": {"type": "string", "description": "The message text."},
				"recipient": {"type": "string", "description": "The receiving agent's name."},
				"priority": {"type": "string", "enum": list(PRIORITIES),
				             "description": "high pings the recipient ahead of normal traffic."}},
				"required": ["content", "recipient"]}}}

	def __call__(self, content: str, recipient: str, priority: str = "normal") -> str:
		return self._policy.send(self._sender, recipient, content, priority)


class ReadMessageTool(Tool):
	"""Native-tool surface for reading: ``read_message()`` returns and marks-read the caller's unread mail."""

	name = "read_message"

	def __init__(self, policy: "MessagingPolicy", reader: str):
		self._policy = policy
		self._reader = reader

	@property
	def schema(self) -> dict:
		return {"type": "function", "function": {
			"name": "read_message",
			"description": "Read your unread messages (marks them as read).",
			"parameters": {"type": "object", "properties": {
				"sender": {"type": "string", "description": "Optionally read only messages from this agent."}},
				"required": []}}}

	def __call__(self, sender: str | None = None) -> str:
		delivered = self._policy.read(self._reader, sender=sender)
		if not delivered:
			return "(no unread messages)"
		return "\n\n".join(f"[from {m.sender} — priority {m.priority}]\n{m.content}" for m in delivered)


class MessagingPolicy(CommunicationPolicy):
	"""Asynchronous point-to-point messaging with per-agent mailboxes and a ping-driven scheduler.

	``fairness_every`` bounds starvation: after that many consecutive ping-driven grants, the
	least-recently-active unpinged agent gets a turn regardless. The protocol text each agent needs is injected
	automatically as a system-block view segment (``PROTOCOL``), so no manual prompt plumbing is required.
	"""

	PROTOCOL = (
		"You work autonomously and communicate with the other agents ONLY by explicit messages.\n"
		"- To send a private message, end your reply with a fenced JSON object:\n"
		'```json\n{"send_message": {"recipient": "<agent name>", "content": "...", "priority": "normal"}}\n```\n'
		'  ("priority": "high" notifies the recipient ahead of normal traffic.)\n'
		"- When you are notified of unread messages, read them by replying with:\n"
		'```json\n{"read_message": {}}\n```\n'
		"  The messages are delivered to you on your next turn.\n"
		"- Otherwise, use your turn to make progress on your task."
	)

	def __init__(self, agents: list[str] | None = None, *, fairness_every: int = 3):
		self.agents = list(agents) if agents is not None else None  # None = all participants
		self.fairness_every = max(1, int(fairness_every))
		self.mailboxes: dict[str, list[Mail]] = {}
		self.events: list[dict] = []  # structured send/read/deliver log, JSON-serializable
		self._turn = 0
		self._pinged_streak = 0
		self._last_spoke: dict[str, int] = {}
		self._read_requests: set[str] = set()  # agents whose fenced-JSON read is pending delivery
		self._delivered: dict[str, list[Mail]] = {}  # mail delivered into an agent's view (stays visible)

	# --- messaging primitives (shared by tools and fenced-JSON parsing) --------------------------------------

	def send(self, sender: str, recipient: str, content: str, priority: str = "normal") -> str:
		if priority not in PRIORITIES:
			priority = "normal"
		mail = Mail(sender=sender, recipient=recipient, content=str(content), priority=priority,
		            sent_at_turn=self._turn)
		self.mailboxes.setdefault(recipient, []).append(mail)
		self.events.append({"event": "send", **mail.to_dict()})
		return f"(message sent to {recipient})"

	def read(self, reader: str, sender: str | None = None) -> list[Mail]:
		"""Mark ``reader``'s unread mail (optionally from one ``sender``) as read and schedule it for delivery
		into the reader's view. Returns the newly delivered items."""
		delivered = []
		for mail in self.mailboxes.get(reader, []):
			if mail.read or (sender is not None and mail.sender != sender):
				continue
			mail.read = True
			delivered.append(mail)
			self.events.append({"event": "read", "reader": reader, **mail.to_dict()})
		# high-priority first, then send order — the order they render in the reader's view
		delivered.sort(key=lambda m: (m.priority != "high", m.sent_at_turn))
		self._delivered.setdefault(reader, []).extend(delivered)
		return delivered

	def unread(self, agent: str) -> list[Mail]:
		return [m for m in self.mailboxes.get(agent, []) if not m.read]

	def tools_for(self, agent: str) -> tuple[Tool, Tool]:
		"""Native ``send_message``/``read_message`` tools bound to ``agent``, for participants with a
		tool-calling family (attach via ``tools=``). The fenced-JSON path needs no setup."""
		return SendMessageTool(self, agent), ReadMessageTool(self, agent)

	# --- CommunicationPolicy hooks ---------------------------------------------------------------------------

	def _agent_names(self, conversation: "Conversation") -> list[str]:
		return self.agents if self.agents is not None else [p.name for p in conversation.participants]

	def next_speaker(self, conversation: "Conversation") -> "Participant | None":
		names = self._agent_names(conversation)
		# 1) an agent whose fenced-JSON read just landed gets the floor to act on the delivered mail
		if self._read_requests:
			name = sorted(self._read_requests)[0]
			self._read_requests.discard(name)
			return self._grant(conversation, name, pinged=True)
		# 2) ping-driven: unread high-priority mail first, then unread normal — unless fairness is due
		pinged = [n for n in names if self.unread(n)]
		if pinged and self._pinged_streak < self.fairness_every:
			pinged.sort(key=lambda n: (not any(m.priority == "high" for m in self.unread(n)),
			                           min(m.sent_at_turn for m in self.unread(n))))
			return self._grant(conversation, pinged[0], pinged=True)
		# 3) fairness tick: the least-recently-active agent
		name = min(names, key=lambda n: self._last_spoke.get(n, -1))
		return self._grant(conversation, name, pinged=False)

	def _grant(self, conversation: "Conversation", name: str, *, pinged: bool) -> "Participant":
		self._pinged_streak = self._pinged_streak + 1 if pinged else 0
		self._last_spoke[name] = self._turn
		self._turn += 1
		return conversation.participant(name)

	def visible(self, message: "Message", pov: "Participant", conversation: "Conversation") -> bool:
		# Autonomous agents: only the moderator framing and one's own turns are in view. Mail arrives via
		# extra_segments after an explicit read. Non-agent participants (e.g. a judge) see everything.
		if pov.name not in self._agent_names(conversation):
			return True
		return message.author in (conversation.moderator_name, pov.name)

	def extra_segments(self, conversation: "Conversation", participant: "Participant") -> list[ViewSegment]:
		if participant.name not in self._agent_names(conversation):
			return []
		segments = [ViewSegment(role="system", content=self.PROTOCOL, origin="system")]
		for mail in self._delivered.get(participant.name, []):
			segments.append(ViewSegment(
				role="user", origin="moderator", author=conversation.moderator_name,
				content=f"[message from {mail.sender} — priority {mail.priority}]\n{mail.content}"))
		pending = self.unread(participant.name)
		if pending:
			high = sum(1 for m in pending if m.priority == "high")
			senders = ", ".join(sorted({m.sender for m in pending}))
			note = (f"[notice] You have {len(pending)} unread message(s) from {senders}"
			        + (f" ({high} high-priority)" if high else "")
			        + '. Read them by replying with ```json\n{"read_message": {}}\n```.')
			segments.append(ViewSegment(role="user", content=note, origin="moderator",
			                            author=conversation.moderator_name))
		return segments

	def on_commit(self, message: "Message", conversation: "Conversation") -> None:
		if message.author not in self._agent_names(conversation):
			return
		sends, read_request = [], None
		for action in parse_json_actions(message.content):
			if isinstance(action.get("send_message"), dict):
				s = action["send_message"]
				if s.get("recipient") and s.get("content") is not None:
					self.send(message.author, str(s["recipient"]), s["content"],
					          str(s.get("priority", "normal")))
					sends.append({"recipient": str(s["recipient"]), "priority": str(s.get("priority", "normal"))})
			if "read_message" in action:
				filt = action.get("read_message") or {}
				read_request = filt.get("sender") if isinstance(filt, dict) else None
				delivered = self.read(message.author, sender=read_request)
				if delivered:
					self._read_requests.add(message.author)
				message.metadata["comm_read"] = [m.to_dict() for m in delivered]
		if sends:
			message.metadata["comm_sends"] = sends

	def reset(self) -> None:
		self.mailboxes.clear()
		self.events.clear()
		self._turn = 0
		self._pinged_streak = 0
		self._last_spoke.clear()
		self._read_requests.clear()
		self._delivered.clear()
