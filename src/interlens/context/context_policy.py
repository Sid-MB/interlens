from __future__ import annotations

from abc import ABC, abstractmethod

from ..view import ViewSegment

# Origins that must never be trimmed by a context policy: the system block, the scenario/moderator seed, and
# private briefings all carry essential framing. Only ``turn`` segments (the growing dialogue middle) are
# eligible for trimming.
PRESERVED_ORIGINS = ("system", "moderator", "private_context")


class ContextPolicy(ABC):
	"""Decides how to fit a participant's view within its model's context window.

	Crucially, ``fit`` runs on the **typed** ``ViewSegment`` list, *before* the family-specific ``finalize_view``
	folds/merges anything. Operating pre-finalize means the policy can reliably preserve the system block and
	moderator seed (their ``origin`` is still intact) and trim only ``turn`` segments, instead of trying to
	reverse-engineer meaning out of already-folded text.
	"""

	@abstractmethod
	def fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]:
		...

	def to_dict(self) -> dict:
		"""Serialize as ``{"kind": ..., **params}``. Subclasses with parameters extend the params; the default
		covers parameterless policies."""
		return {"kind": type(self).__name__}

	@staticmethod
	def _limit(tokenizer, limit: int | None) -> int:
		"""Resolve the effective token budget; falls back to the tokenizer's declared max length."""
		if limit is not None:
			return limit
		return int(getattr(tokenizer, "model_max_length", 1_000_000_000) or 1_000_000_000)

	@staticmethod
	def _seg_tokens(segment: ViewSegment, tokenizer) -> int:
		"""Approximate token cost of a segment's content (ignores per-template wrapper tokens — close enough for
		fitting decisions)."""
		return len(tokenizer(segment.content, add_special_tokens=False).input_ids)

	@classmethod
	def _total_tokens(cls, segments: list[ViewSegment], tokenizer) -> int:
		return sum(cls._seg_tokens(s, tokenizer) for s in segments)
