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

"""Communication topology as a pluggable policy.

A ``Conversation`` has always answered two questions implicitly: *who speaks next* (round-robin over
``participants`` order) and *who sees what* (everyone sees the whole shared transcript). A
``CommunicationPolicy`` makes both answers explicit and swappable, so the same participants, scoring, and
persistence compose with different communication styles:

- ``RoundRobinPolicy`` — the classic shared transcript (the default behavior, now nameable).
- ``DirectPipingPolicy`` — one participant's output becomes the next one's input along a fixed chain,
  formalizing what a 2-party ``Conversation`` already does implicitly and generalizing it to longer pipelines.
- ``MessagingPolicy`` (see ``messaging.py``) — no shared transcript at all: autonomous agents exchange
  point-to-point messages through per-agent mailboxes via ``send_message``/``read_message``, with a
  ping-driven scheduler.

Custom topologies (private sub-group channels, hub-and-spoke, dynamic floor-passing) subclass
``CommunicationPolicy`` and override the same four hooks — no core changes needed. Install a policy via
``Conversation(communication=...)`` (or ``conv.set(communication=...)``); ``run`` consults it for turn order
and the view pipeline consults it for visibility. Policies are conversation-state: a copy-on-write clone /
branch gets an independent deep copy, and they are runtime-only (not persisted by ``save``), like
``message_hooks``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..conversation import Conversation
	from ..message import Message
	from ..participant import Participant
	from ..view import ViewSegment


class CommunicationPolicy(ABC):
	"""Who speaks next, and who sees what.

	Four hooks, all consulted by the ``Conversation`` core:

	- ``next_speaker(conversation)`` — the participant due to speak now, or ``None`` when no one is due (which
	  ends a ``run`` exactly like a stop condition).
	- ``visible(message, pov, conversation)`` — whether a committed transcript message enters ``pov``'s view.
	  Default: everything is visible (the shared-transcript semantics).
	- ``extra_segments(conversation, participant)`` — additional view segments appended after the transcript
	  (delivered mail, pending-message notices, protocol instructions). Default: none.
	- ``on_commit(message, conversation)`` — bookkeeping after a turn is committed (parse message-passing
	  actions, deliver mail, advance scheduling state). Default: no-op.
	"""

	@abstractmethod
	def next_speaker(self, conversation: "Conversation") -> "Participant | None":
		...

	def visible(self, message: "Message", pov: "Participant", conversation: "Conversation") -> bool:
		return True

	def extra_segments(self, conversation: "Conversation", participant: "Participant") -> "list[ViewSegment]":
		return []

	def on_commit(self, message: "Message", conversation: "Conversation") -> None:
		pass

	def reset(self) -> None:
		"""Clear accumulated scheduling/delivery state so one policy instance can drive a fresh conversation."""


class RoundRobinPolicy(CommunicationPolicy):
	"""The shared-transcript default, as an explicit policy: speakers cycle through ``participants`` order and
	everyone sees every committed turn. ``first`` (a name) shifts the starting speaker."""

	def __init__(self, first: str | None = None):
		self.first = first
		self._count = 0

	def next_speaker(self, conversation: "Conversation") -> "Participant | None":
		participants = conversation.participants
		start = 0
		if self.first is not None:
			start = conversation._resolve_participant(self.first)
		speaker = participants[(start + self._count) % len(participants)]
		self._count += 1
		return speaker

	def reset(self) -> None:
		self._count = 0


class DirectPipingPolicy(CommunicationPolicy):
	"""A fixed pipeline: each participant sees only its **predecessor's** output (plus moderator/system framing
	and its own past turns), and speaking order follows the chain — A → B → C → A → …

	This formalizes the natural two-agent dialogue framing (where "the other's turn is my input" is already how
	a 2-party shared transcript renders) and generalizes it to longer chains, where a shared transcript and a
	pipeline genuinely diverge: in a 3-agent pipe, C sees B's output but not A's. Because it is the same
	``Conversation`` machinery, the full transcript is still recorded and serialized — visibility filters what
	each *model* is conditioned on, never what the record keeps."""

	def __init__(self, chain: list[str] | None = None):
		self.chain = list(chain) if chain is not None else None  # participant names; None = participants order
		self._count = 0

	def _order(self, conversation: "Conversation") -> list[str]:
		return self.chain if self.chain is not None else [p.name for p in conversation.participants]

	def next_speaker(self, conversation: "Conversation") -> "Participant | None":
		order = self._order(conversation)
		name = order[self._count % len(order)]
		self._count += 1
		return conversation.participant(name)

	def visible(self, message: "Message", pov: "Participant", conversation: "Conversation") -> bool:
		if message.author in (conversation.moderator_name, pov.name):
			return True  # framing and one's own past turns are always in view
		order = self._order(conversation)
		if pov.name not in order:
			return True  # participants outside the chain (e.g. a judge) see everything
		predecessor = order[(order.index(pov.name) - 1) % len(order)]
		return message.author == predecessor

	def reset(self) -> None:
		self._count = 0
