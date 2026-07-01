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


class SlidingWindowPolicy(ContextPolicy):
	"""Keep the preserved framing plus the most recent ``keep_last`` turns; drop older turns.

	``keep_system=True`` (the default) preserves the system/moderator/private_context framing regardless of the
	window; set it False to also let framing fall outside the window (rarely wanted). Unlike ``DropOldestPolicy``
	this is a fixed-size window rather than a fit-to-budget trim, so it's predictable turn-to-turn.
	"""

	def __init__(self, keep_last: int, keep_system: bool = True):
		self.keep_last = keep_last
		self.keep_system = keep_system

	def to_dict(self) -> dict:
		return {"kind": "SlidingWindowPolicy", "keep_last": self.keep_last, "keep_system": self.keep_system}

	def fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]:
		turn_indices = [i for i, s in enumerate(segments) if s.origin == "turn"]
		keep_turns = set(turn_indices[-self.keep_last:]) if self.keep_last > 0 else set()

		kept = []
		for i, s in enumerate(segments):
			if s.origin == "turn":
				if i in keep_turns:
					kept.append(s)
			elif self.keep_system:
				kept.append(s)
		return kept
