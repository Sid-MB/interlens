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
