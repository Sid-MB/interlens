from __future__ import annotations

from dataclasses import dataclass

from .participant.role import Role


@dataclass
class ContextItem:
	"""A single item of *private* asymmetric knowledge given to one participant (a briefing, a document, a fact).

	Deliberately distinct from ``Message``: a briefing is not a dialogue turn — it has no turn index and its
	``author`` is nominal — so overloading ``Message`` would give it misleading turn/authorship semantics.

	Role semantics are pinned rather than role-swapped: a briefing renders by default as **user-provided
	context** (``role_hint=USER``) — the participant reads it as information handed to it, not as its own prior
	speech — with ``SYSTEM`` available for standing private instructions. Private context is injected only into
	the owning participant's view and never enters the shared transcript.
	"""

	content: str
	role_hint: Role = "user"
	author: str = "moderator"
