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


class DropOldestPolicy(ContextPolicy):
	"""Drop the oldest ``turn`` segments (preserving system/moderator/private_context) until the view fits."""

	def fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]:
		budget = self._limit(tokenizer, limit)
		if self._total_tokens(segments, tokenizer) <= budget:
			return segments

		# Indices of trimmable turns, oldest first.
		turn_indices = [i for i, s in enumerate(segments) if s.origin == "turn"]
		dropped: set[int] = set()
		total = self._total_tokens(segments, tokenizer)
		for i in turn_indices:
			if total <= budget:
				break
			total -= self._seg_tokens(segments[i], tokenizer)
			dropped.add(i)

		kept = [s for i, s in enumerate(segments) if i not in dropped]
		# If preserved framing alone still overflows, there's nothing left to trim — surface it rather than lie.
		if self._total_tokens(kept, tokenizer) > budget:
			raise ValueError(
				f"cannot fit view within {budget} tokens even after dropping all turns "
				f"(preserved {PRESERVED_ORIGINS} framing is too large)"
			)
		return kept
