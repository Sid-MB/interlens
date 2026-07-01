from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .participant.role import Role

# Where a rendered segment came from. Origin is what lets the context policy trim safely: it preserves
# ``system``/``moderator``/``private_context`` and only drops middle ``turn`` segments — and it does so on
# these *typed* segments BEFORE the family-specific (possibly lossy) ``finalize_view`` folds/merges them.
Origin = Literal["system", "moderator", "private_context", "turn"]


@dataclass
class ViewSegment:
	"""One entry in a participant's *structured* view, before it is flattened to the ``[{role, content}]`` shape
	a chat template consumes.

	Carrying ``origin`` (and ``author`` for turns) through the pipeline is the whole point: it keeps the
	semantic identity of each piece intact so context-trimming and author-labelling can act on it, rather than
	reverse-engineering meaning out of already-folded text.
	"""

	role: Role
	content: str
	origin: Origin
	author: str | None = None

	def as_message(self) -> dict:
		"""Flatten to the ``{"role", "content"}`` dict a chat template expects."""
		return {"role": self.role, "content": self.content}
