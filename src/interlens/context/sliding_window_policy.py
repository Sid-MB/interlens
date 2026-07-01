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
