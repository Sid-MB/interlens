# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
