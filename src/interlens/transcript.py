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

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from .message import Message

if TYPE_CHECKING:
	from .participant import Participant
	from .participant.participants.model_participant import ModelParticipant

# Bumped when the on-disk shape changes; load() dispatches migrations off it. Currently an honest placeholder
# (no migrations exist yet) — the version is recorded so future readers can upgrade old files.
SCHEMA_VERSION = 1

# A reference to one turn in a transcript: an ``int`` position (Python indexing — negatives count from the end)
# or the ``Message`` object itself (located by identity, ``is``, in ``resolve_index``).
MessageRef = Message | int


class _ConcatMessages(Sequence):
	"""A read-only lazy concatenation of a base message list + a small ``extra`` tuple, backing ``with_extra``.

	The base list is referenced, not copied — only ``extra`` is materialized — so extending a long transcript is
	O(len(extra)), not O(len(transcript)). It supports the read access ``Transcript`` needs (``len`` / indexing /
	iteration) and is intentionally immutable; ``append`` raises so the ephemeral view can't be mistaken for a
	mutable transcript (``Transcript.copy()`` gives a real, mutable one)."""

	__slots__ = ("_base", "_extra")

	def __init__(self, base: "list[Message]", extra: "tuple[Message, ...]"):
		self._base = base
		self._extra = tuple(extra)

	def __len__(self) -> int:
		return len(self._base) + len(self._extra)

	def __iter__(self):
		yield from self._base
		yield from self._extra

	def __getitem__(self, index):
		if isinstance(index, slice):
			return list(self)[index]
		n = len(self)
		if index < 0:
			index += n
		if not 0 <= index < n:
			raise IndexError("transcript index out of range")
		nb = len(self._base)
		return self._base[index] if index < nb else self._extra[index - nb]

	def append(self, *_):
		raise TypeError("this is a read-only with_extra() view; call Transcript.copy() for a mutable transcript")


@dataclass
class Transcript:
	"""The canonical, perspective-neutral record of a conversation, plus the logic to render it *from* a given
	participant's perspective.

	Design: the transcript never commits to ``assistant``/``user`` roles. Each message just knows its ``author``.
	When it's a participant's turn, ``render_roles`` maps that neutral record into the chat-template ``[{role,
	content}]`` shape *from that participant's point of view* — its own turns become ``self_role`` (normally
	``assistant``), everyone else's become ``others_role`` (normally ``user``). This single trick is why two
	different models with different tokenizers can share one transcript: each gets the view its own template
	expects, and the stored record stays singular.

	P0 scope: this holds only the message list + rendering + list-like ergonomics. Serialization, context
	policies, author-labelling for N-party, and reasoning re-injection are layered on in later phases.
	"""

	messages: list[Message] = field(default_factory=list)

	def append(self, author: str, content: str, **metadata) -> Message:
		"""Append a committed turn and return it. ``metadata`` captures anything non-authoritative (parsed
		reasoning, logprobs, tool trails) without polluting ``content``."""
		message = Message(author=author, content=content, metadata=dict(metadata))
		self.messages.append(message)
		return message

	def with_extra(self, *extra: Message) -> "Transcript":
		"""Return a lightweight, ephemeral **read-only** ``Transcript`` = this one's messages followed by ``extra``,
		backed by a lazy concatenation (``_ConcatMessages``): the base message list is **not copied** — only
		``extra`` is materialized, so this is O(len(extra)), not O(len(transcript)), and ``Message`` objects are
		shared by reference. The original is untouched.

		This is the data-layer primitive behind ephemeral sampling ("what would a participant say if ``extra`` had
		just been said?"): build the extended transcript, render it, discard it —
		``transcript.with_extra(Message("bob", "…")).render_roles(pov=alice)``. The result is read-only (rendering,
		``len``, indexing, iteration all work; appending raises — ``copy()`` first if you need a mutable one).

		(A one-shot generator was rejected: ``Transcript`` needs ``len`` / indexing / repeated iteration, which a
		generator can't provide.)"""
		return Transcript(_ConcatMessages(self.messages, extra))

	def render_roles(self, *, pov: "Participant") -> list[dict]:
		"""Render **the transcript turns only** as ``[{"role", "content"}]`` from ``pov``'s perspective (``pov`` is
		keyword-only: ``render_roles(pov=alice)``). Its own turns become ``self_role`` (normally ``assistant``),
		everyone else's become ``others_role`` (normally ``user``). For a "what if X had just been said" render,
		extend first with ``with_extra`` and render the result.

		**Limitation — this is NOT what the model actually sees.** The ``Transcript`` is the perspective-neutral
		record; it knows nothing about a participant's ``system_prompt`` / ``private_context``, the conversation's
		``shared_system_prompt`` / ``shared_context`` framing, the ``context_policy`` fitting, or the family-specific
		flatten (Gemma system-folding etc.). Those are added by the ``Conversation`` pipeline. For the **real**
		generation input use ``Conversation.view(pov)`` (or ``Conversation.render_templated(pov)`` for the templated
		string); use this method for lower-level inspection of the record itself."""
		rendered = []
		for message in self.messages:
			role = pov.self_role if message.author == pov.name else pov.others_role
			rendered.append({"role": role, "content": message.content})
		return rendered

	def render_templated(self, *, pov: "ModelParticipant",
	                     add_generation_prompt: bool = False, tokenize: bool = False):
		"""
		Template **the transcript turns only** from ``pov``'s point of view — i.e. ``render_roles`` role-swapped,
		then run through ``pov``'s tokenizer chat template so the special / control tokens (``<|im_start|>assistant``
		etc.) are included. ``pov`` is keyword-only: call ``render_templated(pov=alice)``. Returns a str
		(``tokenize=False``, default) or token ids (``tokenize=True``); ``add_generation_prompt`` appends the
		assistant open tag.

		**Prefer ``Conversation.render_templated`` if you have access to a conversation**: it adds the system prompt, private context, context-fitting, and family-specific flattening, printing the exact input models see.

		### Limitations
		**NOT the exact model input.** This omits the system prompt, private context, context-fitting,
		and the family-specific flatten that a real turn also gets (see ``render_roles``); it also renders the raw
		role-swapped turns as-is, which can even *raise* for families needing strict alternation / system-folding
		(e.g. Gemma) since the merge isn't applied. For the **exact, family-correct prompt the model actually sees**,
		use ``Conversation.render_templated(pov)``. This method is a lower-level inspection of the record. Requires a
		local model participant (with a tokenizer); an API participant has none and raises."""
		tokenizer = getattr(pov, "tokenizer", None)
		if tokenizer is None:
			raise TypeError(f"{type(pov).__name__} {getattr(pov, 'name', '')!r} has no tokenizer; "
			                f"render_templated needs a local ModelParticipant. If you have a conversation, use `conversation.render_templated(pov='participant_name')` or `transcript.render_templated(pov=conversation.participant('participant_name'))` instead.")
		view = self.render_roles(pov=pov)
		return tokenizer.apply_chat_template(view, tokenize=tokenize, add_generation_prompt=add_generation_prompt)

	def copy(self) -> "Transcript":
		"""Deep-ish copy of the message list for branching. Messages are small string records, so this is cheap;
		the invariant that keeps it cheap is that heavy tensors never live in ``Message.metadata``."""
		return Transcript([Message(m.author, m.content, dict(m.metadata)) for m in self.messages])

	# --- in-place history editing --------------------------------------------------------------------------
	# These mutate the record in place (and return ``self`` for chaining). Branch first (``Transcript.copy`` /
	# ``Conversation.branch``) if you want to keep the original intact. Note ``Message`` is a mutable dataclass and
	# the transcript stores it *by reference* — so editing a message directly (``transcript[i].content = "…"`` or
	# holding onto the object ``append``/``sample`` returned) is already reflected everywhere; ``edit`` is just a
	# convenience wrapper around that.

	def resolve_index(self, ref: "MessageRef") -> int:
		"""Normalize a message reference to a concrete ``[0, len)`` position. ``ref`` is either an ``int`` index
		(Python semantics — negatives count from the end, ``-1`` = last turn) or a ``Message`` **object**, located
		by identity (``is``, not equality — two turns with the same text are still distinct). Raises ``IndexError``
		for an out-of-range int and ``ValueError`` for a message that isn't in this transcript."""
		if isinstance(ref, Message):
			for i, m in enumerate(self.messages):
				if m is ref:
					return i
			raise ValueError("message is not in this transcript")
		n = len(self.messages)
		i = ref + n if ref < 0 else ref
		if not 0 <= i < n:
			raise IndexError(f"message index {ref} out of range for transcript of length {n}")
		return i

	def truncate(self, length: int) -> "Transcript":
		"""Keep only the first ``length`` turns, dropping everything after (mutates in place, returns ``self``).
		``length`` is a *count*, clamped to ``[0, len]``: over-long values are a no-op and negatives count from the
		end (``-1`` keeps all but the last turn). To cut relative to a specific message, use ``resolve_index`` /
		``rewind(to=…)`` instead."""
		if length < 0:
			length = max(0, len(self.messages) + length)
		del self.messages[length:]
		return self

	def rewind(self, *, to: "MessageRef") -> "Transcript":
		"""Rewind so the turn referenced by ``to`` becomes the new last turn — i.e. drop everything **after** it,
		keeping ``to`` itself (mutates in place, returns ``self``). ``to`` is a ``MessageRef``: an ``int`` index
		(negatives count from the end — ``rewind(to=-2)`` takes back the single last turn) or a ``Message`` object
		matched by identity. To drop all turns use ``clear``."""
		return self.truncate(self.resolve_index(to) + 1)

	def clear(self) -> "Transcript":
		"""Drop **every** turn, returning ``self``.

		⚠️ This wipes the whole record, including any leading seed turn — the ``shared_context`` scenario framing and
		any moderator/initial-instruction turns injected at construction. Nothing about the conversation's opening
		setup survives. If you want to clear the *dialogue* but keep that framing (e.g. to rerun the same scenario),
		call ``Conversation.reset`` instead, which empties and then re-seeds the ``shared_context`` turn."""
		self.messages.clear()
		return self

	def edit(self, ref: "MessageRef", content: str | None = None, *, author: str | None = None, **metadata) -> Message:
		"""Edit a committed past turn in place and return it. ``ref`` is a ``MessageRef`` (int index, negatives
		allowed, or a ``Message`` object matched by identity). Only the arguments you pass are changed: ``content``
		and/or ``author`` are replaced when given; ``metadata`` keys are merged over the existing metadata (pass an
		explicit key to overwrite it — untouched keys are left alone). Editing the ``Message`` object's fields
		directly does the same thing, since the transcript holds it by reference."""
		message = self.messages[self.resolve_index(ref)]
		if content is not None:
			message.content = content
		if author is not None:
			message.author = author
		if metadata:
			message.metadata.update(metadata)
		return message

	def pretty(self, metadata: bool = False) -> str:
		"""A human-readable dump for debugging: one ``[i] author: content`` block per turn. With ``metadata=True``,
		also list each turn's non-empty metadata (parsed reasoning, tool trail, token counts, …). Also what
		``str(transcript)`` / ``print(transcript)`` uses (without metadata)."""
		lines = []
		for i, m in enumerate(self.messages):
			lines.append(f"[{i}] {m.author}: {m.content}")
			if metadata and m.metadata:
				for k, v in m.metadata.items():
					lines.append(f"      · {k}: {v}")
		return "\n".join(lines)

	def __str__(self) -> str:
		return self.pretty()

	def __len__(self) -> int:
		return len(self.messages)

	def __iter__(self) -> Iterator[Message]:
		return iter(self.messages)

	def __getitem__(self, index):
		# List-like ergonomics: an int yields a Message, a slice yields a new Transcript.
		if isinstance(index, slice):
			return Transcript(self.messages[index])
		return self.messages[index]

	# --- serialization (level 1) ---------------------------------------------------------------------------

	def to_dict(self) -> dict:
		return {
			"schema_version": SCHEMA_VERSION,
			"messages": [{"author": m.author, "content": m.content, "metadata": m.metadata} for m in self.messages],
		}

	@classmethod
	def from_dict(cls, data: dict) -> "Transcript":
		# Migration dispatch would key off data["schema_version"] here once a v2 exists.
		return cls([Message(m["author"], m["content"], m.get("metadata", {})) for m in data["messages"]])

	def save(self, path: str | Path) -> None:
		Path(path).write_text(json.dumps(self.to_dict(), indent=2))

	@classmethod
	def load(cls, path: str | Path) -> "Transcript":
		"""Load a transcript from disk. Works with no models present (for scoring/analysis of saved runs)."""
		return cls.from_dict(json.loads(Path(path).read_text()))
