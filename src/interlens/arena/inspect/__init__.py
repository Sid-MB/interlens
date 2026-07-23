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

"""Optional Inspect (inspect-ai) integration: run arena scenarios under ``inspect eval``.

Install with the extra: ``pip install interlens[inspect]``. Exposes the bundled scenarios as Inspect
``Task``s — instance banks as samples, the arena engine wrapped as a custom solver (any Inspect-supported
model plays every seat), and the exact scenario scorers as Inspect scorers::

    inspect eval interlens.arena.inspect/info_relay --model anthropic/claude-sonnet-5

See ``tasks.py`` for the task parameters (level, arm, situational cells, communication mode, instance count).
"""
from __future__ import annotations

try:
	import inspect_ai  # noqa: F401
except ImportError as _err:  # pragma: no cover - exercised only without the extra
	raise ImportError(
		"interlens.arena.inspect requires the optional 'inspect-ai' dependency. "
		"Install it with: pip install interlens[inspect]"
	) from _err

from .adapter import InspectModelParticipant, arena_solver, scenario_scorer
from .tasks import coding_collab, distributed_longcontext, info_relay, negotiation, security_dilemma

__all__ = ["negotiation", "info_relay", "security_dilemma", "coding_collab", "distributed_longcontext",
           "arena_solver", "scenario_scorer", "InspectModelParticipant"]
