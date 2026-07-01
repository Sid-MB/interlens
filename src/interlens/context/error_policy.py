from __future__ import annotations

from .context_policy import ContextPolicy
from ..view import ViewSegment


class ErrorPolicy(ContextPolicy):
	"""The safe default: raise if the view exceeds the context window rather than silently dropping content.

	Silent truncation reads as "everything fit" when it didn't, which is exactly the kind of quiet data loss this
	harness avoids. Callers who want trimming opt into ``DropOldestPolicy``/``SlidingWindowPolicy`` explicitly.
	"""

	def fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]:
		budget = self._limit(tokenizer, limit)
		total = self._total_tokens(segments, tokenizer)
		if total > budget:
			raise ValueError(
				f"view ~{total} tokens exceeds context limit {budget}; choose a DropOldest/SlidingWindow "
				f"context policy or shorten the scenario"
			)
		return segments
