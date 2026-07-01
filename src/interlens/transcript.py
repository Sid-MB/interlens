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
		"""Render the transcript as ``[{"role", "content"}]`` from ``pov``'s perspective (``pov`` is keyword-only:
		call ``render_roles(pov=alice)``). Its own turns become ``self_role`` (normally ``assistant``), everyone
		else's become ``others_role`` (normally ``user``). For a "what if X had just been said" render, extend
		first with ``with_extra`` and render the result."""
		rendered = []
		for message in self.messages:
			role = pov.self_role if message.author == pov.name else pov.others_role
			rendered.append({"role": role, "content": message.content})
		return rendered

	def render_templated(self, *, pov: "ModelParticipant",
	                     add_generation_prompt: bool = False, tokenize: bool = False):
		"""Render the transcript from ``pov``'s point of view as the **templated prompt its model actually sees** —
		i.e. ``render_roles`` role-swapped, then run through ``pov``'s tokenizer chat template so the special /
		control tokens (``<|im_start|>assistant`` etc.) are included. ``pov`` is keyword-only: call
		``render_templated(pov=alice)``. Returns a str (``tokenize=False``, default) or token ids
		(``tokenize=True``); ``add_generation_prompt`` appends the assistant open tag.

		Scope: this is the **transcript turns only** — the system prompt, private context, and context-fitting that
		a real turn also sees are added by the ``Conversation`` view pipeline, not here. It also renders the raw
		role-swapped turns as-is, so for families that require strict role alternation / system-folding (e.g.
		Gemma) prefer building the view via ``Conversation`` when you need the exact, family-correct prompt. Great
		for debugging what a specific model is conditioned on. Requires a local model participant (with a
		tokenizer); an API participant has none and raises."""
		tokenizer = getattr(pov, "tokenizer", None)
		if tokenizer is None:
			raise TypeError(f"{type(pov).__name__} {getattr(pov, 'name', '')!r} has no tokenizer; "
			                f"render_templated needs a local ModelParticipant")
		view = self.render_roles(pov=pov)
		return tokenizer.apply_chat_template(view, tokenize=tokenize, add_generation_prompt=add_generation_prompt)

	def copy(self) -> "Transcript":
		"""Deep-ish copy of the message list for branching. Messages are small string records, so this is cheap;
		the invariant that keeps it cheap is that heavy tensors never live in ``Message.metadata``."""
		return Transcript([Message(m.author, m.content, dict(m.metadata)) for m in self.messages])

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
