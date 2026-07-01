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

from .context_policy import ContextPolicy, PRESERVED_ORIGINS
from ..view import ViewSegment


class SummarizePolicy(ContextPolicy):
	"""Compress older turns into a single summary segment instead of dropping them outright (the heaviest
	policy).

	Keeps the preserved framing (system / moderator / private_context) and the most recent ``keep_last`` turns
	verbatim, and replaces the older middle turns with one summary segment produced by ``summarizer`` — a
	callable ``list[str] -> str`` over the dropped turns' contents. With no summarizer it inserts a neutral
	placeholder, so it degrades to a labelled drop rather than silently losing content.

	``summarizer`` is a live callable and so is not serialized; a loaded template gets ``summarizer=None`` and
	the caller re-injects one if needed.
	"""

	def __init__(self, keep_last: int = 4, summarizer=None):
		self.keep_last = keep_last
		self.summarizer = summarizer

	def to_dict(self) -> dict:
		return {"kind": "SummarizePolicy", "keep_last": self.keep_last}

	def _summarize(self, texts: list[str]) -> str:
		if self.summarizer is not None:
			return self.summarizer(texts)
		return f"[{len(texts)} earlier turns omitted]"

	def fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]:
		budget = self._limit(tokenizer, limit)
		if self._total_tokens(segments, tokenizer) <= budget:
			return segments

		preserved = [s for s in segments if s.origin in PRESERVED_ORIGINS]
		turns = [s for s in segments if s.origin == "turn"]
		older = turns[: -self.keep_last] if self.keep_last > 0 else turns
		recent = turns[-self.keep_last:] if self.keep_last > 0 else []
		if not older:
			return segments  # nothing old enough to summarize; leave as-is

		summary = ViewSegment(role="user", origin="moderator",
		                      content="[Summary of earlier conversation]\n" + self._summarize([s.content for s in older]))
		# Preserve original ordering: framing first, then the summary standing in for older turns, then recent.
		return preserved + [summary] + recent
