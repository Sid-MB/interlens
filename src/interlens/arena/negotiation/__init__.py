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

# [rational_agents scaffold: oracles-strategies] 2026-07-23 — package seeded minimally by T3.
# Deliberately NO eager submodule imports: this package is co-authored (game-theory owns
# space/sheets/solutions/generate/references.py; oracles-strategies owns beliefs/acceptance/
# bestresponse/equilibrium/strategies.py + _oracle_common.py), and eager imports would fail
# while a sibling's file is still absent. Import submodules explicitly, e.g.
# ``from interlens.arena.negotiation.beliefs import BeliefOracle``. Convenience re-exports can be
# added here at integration time once every sibling module has landed.

"""Multi-issue, multi-party scorable negotiation: deal spaces, private score sheets, exact solution
concepts, computable rational-agent oracles, and an executable strategy zoo.

See ``experiments/rational_agents/DESIGN.md`` §4 (oracle stack) and
``docs/lit/rational-oracles.md`` for the literature grounding behind each module."""
