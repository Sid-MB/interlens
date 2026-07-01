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

from __future__ import annotations

from abc import ABC, abstractmethod

from .role import Role
from ..message import Message
from ..view import ViewSegment


class Participant(ABC):
	"""A participant in a conversation, either a model or a person.

	A participant owns three things: an *identity* within the conversation (``name`` + ``self_role``/
	``others_role``), its *private framing* (``system_prompt`` + ``private_context`` — instructions/knowledge
	only it sees), and the ability to turn a rendered view into its next message (``generate``). The
	``Conversation`` assembles the structured view from the shared transcript; the participant flattens that view
	to what its chat template expects via ``finalize_view`` and generates.
	"""

	name: str
	"""A name or identifier to uniquely identify this participant within a conversation."""

	# Near-universal default mapping; overridden only by API/other-family/N-party participants (rare).
	self_role: Role = "assistant"
	others_role: Role = "user"

	# Private framing. Defaults live here so the base view-assembly logic works for any participant type;
	# dataclass subclasses redeclare these as fields.
	system_prompt: str | None = None
	private_context: tuple = ()

	# Family capability flags. The base ``finalize_view`` uses these to decide how to flatten the structured
	# view, so a new family gets correct behavior by setting flags rather than reimplementing the flatten.
	supports_system_role: bool = True
	requires_alternating_roles: bool = False

	@abstractmethod
	def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
	             return_logprobs: bool = False, turn: int | None = None,
	             max_new_tokens: int | None = None) -> Message:
		"""Produce this participant's next message given ``view`` — the conversation flattened to
		``[{"role", "content"}]`` from this participant's perspective. Returns a ``Message`` it authored.

		Interp options apply to local-model participants: ``steering`` (a ``SteeringSpec``), ``capture`` (a
		``CaptureRequest``), ``patch`` (a ``Patch``), and ``return_logprobs``; ``turn`` is the message index used
		to tag captured activations. Participants that can't honor an interp request (e.g. API-backed) must raise
		rather than silently ignore it — a failed capture/steer must fail loudly."""
		...

	def finalize_view(self, segments: list[ViewSegment]) -> list[dict]:
		"""Flatten the structured, context-fitted view into the ``[{role, content}]`` list the chat template
		consumes. Applies family-specific repairs driven by the capability flags:

		- ``supports_system_role=False`` → fold the leading system content into the first user turn (Gemma's
		  template errors on a standalone ``system`` role).
		- ``requires_alternating_roles=True`` → merge consecutive same-role segments (Gemma requires strict
		  user/model alternation; the moderator seed + another speaker + private context can otherwise produce
		  consecutive ``user`` turns that the template rejects). Merged turns keep author labels so speaker
		  identity isn't lost in the concatenation.
		"""
		segments = list(segments)
		if not self.supports_system_role:
			segments = self._fold_system_into_first_user(segments)
		if self.requires_alternating_roles:
			return self._merge_consecutive_same_role(segments)
		return [s.as_message() for s in segments]

	@staticmethod
	def _fold_system_into_first_user(segments: list[ViewSegment]) -> list[ViewSegment]:
		system_text = "\n\n".join(s.content for s in segments if s.role == "system")
		rest = [s for s in segments if s.role != "system"]
		if not system_text:
			return rest
		for i, s in enumerate(rest):
			if s.role == "user":
				merged = f"{system_text}\n\n{s.content}"
				rest[i] = ViewSegment(role="user", content=merged, origin=s.origin, author=s.author)
				return rest
		# No user turn to fold into: promote the system text to a leading user turn.
		return [ViewSegment(role="user", content=system_text, origin="system"), *rest]

	@staticmethod
	def _merge_consecutive_same_role(segments: list[ViewSegment]) -> list[dict]:
		out: list[dict] = []
		group: list[ViewSegment] = []

		def flush():
			if not group:
				return
			role = group[0].role
			# If the merged run spans multiple distinct authors, prefix each part with its author to preserve
			# who-said-what through the lossy merge (also the seam N-party rendering will use).
			authors = {s.author for s in group if s.author}
			if len(authors) > 1:
				parts = [f"{s.author}: {s.content}" if s.author else s.content for s in group]
			else:
				parts = [s.content for s in group]
			out.append({"role": role, "content": "\n\n".join(parts)})
			group.clear()

		for s in segments:
			if group and s.role != group[-1].role:
				flush()
			group.append(s)
		flush()
		return out
