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
	             max_new_tokens: int | None = None, seat: str | None = None) -> Message:
		"""Produce this participant's next message given ``view`` — the conversation flattened to
		``[{"role", "content"}]`` from this participant's perspective. Returns a ``Message`` it authored.

		Interp options apply to local-model participants: ``steering`` (a ``SteeringSpec``), ``capture`` (a
		``CaptureRequest``), ``patch`` (a ``Patch``), and ``return_logprobs``; ``turn`` is the message index used
		to tag captured activations. Participants that can't honor an interp request (e.g. API-backed) must raise
		rather than silently ignore it — a failed capture/steer must fail loudly.

		``seat`` is WHICH SEAT this turn is being spoken for, passed by the arena engine straight from
		``SeatRequest.seat`` (``None`` outside the arena, e.g. a plain ``Conversation``). Most participants ignore
		it — the view already addresses them — but a participant that fronts several seats needs to know which one
		it is answering as, and reading that from the request is exact where recovering it from the prompt text is
		guesswork that breaks whenever the wording changes."""
		...

	def finalize_view(self, segments: list[ViewSegment]) -> list[dict]:
		"""Flatten the structured, context-fitted view into the ``[{role, content}]`` list the chat template
		consumes. Applies family-specific repairs driven by the capability flags:

		- ``supports_system_role=False`` → fold the leading system content into the first user turn (Gemma-2's
		  template errors on a standalone ``system`` role).
		- ``requires_alternating_roles=True`` → merge consecutive same-role segments (Gemma requires strict
		  user/model alternation; the moderator seed + another speaker + private context can otherwise produce
		  consecutive ``user`` turns that the template rejects). Merged turns keep author labels so speaker
		  identity isn't lost in the concatenation.

		The dict-level tail of the same repairs lives in :meth:`repair_view`, which this delegates to (and which
		participants handed an ALREADY-flattened view — arena scenarios build their per-seat views as plain
		``[{role, content}]`` lists — call directly). Both are idempotent, so running them twice is a no-op.
		"""
		segments = list(segments)
		if not self.supports_system_role:
			segments = self._fold_system_into_first_user(segments)
		messages = (self._merge_consecutive_same_role(segments) if self.requires_alternating_roles
		            else [s.as_message() for s in segments])
		return self.repair_view(messages)

	def repair_view(self, messages: list[dict]) -> list[dict]:
		"""Apply this family's chat-template repairs to an **already-flattened** ``[{role, content}]`` view, so a
		view that never went through :meth:`finalize_view` (an arena scenario builds its per-seat views directly)
		still renders under a strict template. Idempotent; a no-op for permissive families (both flags at their
		default), which is why every render path can call it unconditionally.

		With ``requires_alternating_roles`` two repairs run, in order:

		1. **merge** consecutive same-role turns (joined with a blank line) — a seat that speaks twice in a row
		   (the round-boundary/rotation repeat in a multi-party game) otherwise emits two ``assistant`` turns.
		2. **user-first**: a strict template (Gemma, Mistral/Ministral) requires the first turn after the optional
		   leading ``system`` to be ``user``, so a view that opens with the seat's OWN turn — the opener of a
		   multi-round game, whose first event in the shared log is its own proposal — is repaired by inserting one
		   minimal placeholder ``user`` turn there. Insertion, not re-roling: every existing turn keeps its role
		   and text, so a family that renders ``system`` in its own tokens (Mistral's ``[SYSTEM_PROMPT]``) keeps
		   that framing, and the seat's own words are never re-attributed to anyone else.
		"""
		messages = [dict(m) for m in messages]
		if not self.supports_system_role:
			messages = self._fold_system_into_first_user_messages(messages)
		if self.requires_alternating_roles:
			messages = self._merge_same_role_messages(messages)
			messages = self._ensure_user_first(messages)
		return messages

	# --------------------------------------------------------------------------------- repair primitives ---
	# Shared by the segment-level (``finalize_view``) and dict-level (``repair_view``) paths so the family rules
	# have exactly one implementation each.

	@staticmethod
	def _same_role_runs(items: list, role_of) -> list[list]:
		"""``items`` grouped into maximal runs of consecutive equal ``role_of(item)``."""
		runs: list[list] = []
		for item in items:
			if runs and role_of(item) == role_of(runs[-1][-1]):
				runs[-1].append(item)
			else:
				runs.append([item])
		return runs

	@staticmethod
	def _fold_system_into_first_user(segments: list[ViewSegment]) -> list[ViewSegment]:
		system_text = "\n\n".join(s.content for s in segments if s.role == "system")
		rest = [s for s in segments if s.role != "system"]
		if not system_text:
			return rest
		# Fold only into a user turn that OPENS the view; folding into a later one (past the seat's own turns)
		# would both misplace the framing and leave the view starting on ``assistant``.
		if rest and rest[0].role == "user":
			first = rest[0]
			rest[0] = ViewSegment(role="user", content=f"{system_text}\n\n{first.content}",
			                      origin=first.origin, author=first.author)
			return rest
		return [ViewSegment(role="user", content=system_text, origin="system"), *rest]

	@classmethod
	def _merge_consecutive_same_role(cls, segments: list[ViewSegment]) -> list[dict]:
		out: list[dict] = []
		for run in cls._same_role_runs(segments, lambda s: s.role):
			# If the merged run spans multiple distinct authors, prefix each part with its author to preserve
			# who-said-what through the lossy merge (also the seam N-party rendering will use).
			authors = {s.author for s in run if s.author}
			if len(authors) > 1:
				parts = [f"{s.author}: {s.content}" if s.author else s.content for s in run]
			else:
				parts = [s.content for s in run]
			out.append({"role": run[0].role, "content": "\n\n".join(parts)})
		return out

	@classmethod
	def _fold_system_into_first_user_messages(cls, messages: list[dict]) -> list[dict]:
		"""``_fold_system_into_first_user`` on plain message dicts (no origin/author to preserve)."""
		system_text = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
		rest = [m for m in messages if m["role"] != "system"]
		if not system_text:
			return rest
		if rest and rest[0]["role"] == "user":
			return [{"role": "user", "content": f"{system_text}\n\n{rest[0]['content']}"}, *rest[1:]]
		return [{"role": "user", "content": system_text}, *rest]

	@classmethod
	def _merge_same_role_messages(cls, messages: list[dict]) -> list[dict]:
		return [{"role": run[0]["role"], "content": "\n\n".join(m["content"] for m in run)}
		        for run in cls._same_role_runs(messages, lambda m: m["role"])]

	# Opens a view whose first real turn is the seat's own. Deliberately contentless: it exists to satisfy the
	# template's user-first assertion, so it must not add anything a model could mistake for an instruction.
	OPENING_USER_PLACEHOLDER = "(The conversation so far follows.)"

	@classmethod
	def _ensure_user_first(cls, messages: list[dict]) -> list[dict]:
		"""Guarantee the first turn after an optional leading ``system`` is ``user`` (what a strict-alternation
		template asserts — Gemma and Mistral phrase the same rule differently) by INSERTING a placeholder user
		turn there. Nothing already in the view is re-roled or rewritten."""
		lead = 1 if messages and messages[0]["role"] == "system" else 0
		if len(messages) <= lead or messages[lead]["role"] == "user":
			return messages
		return [*messages[:lead], {"role": "user", "content": cls.OPENING_USER_PLACEHOLDER}, *messages[lead:]]
