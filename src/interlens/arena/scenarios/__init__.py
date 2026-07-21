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

"""Bundled scenarios, four families:

- ``Negotiation`` — multi-issue, multi-party deal-making with secret score sheets (exact enumeration).
- ``InfoRelay`` — wrong-shard epistemics: can a team relay a correct fact past a confident wrong holder.
- ``SecurityDilemma`` — repeated 2-party build/deescalate/attack with an absorbing war spiral and noisy
  intelligence (payoff-exact scoring; no solo arm).
- ``CodingCollab`` — 3 seats jointly write one Python module against a public pytest suite while each holds
  private, mechanically checkable style constraints (sandboxed exact scoring).
- ``DistributedLongContext`` — one long-context task partitioned across 4 seats (task adapters + offline
  instance builders in ``interlens.arena.scenarios.dlc``; first-class ``truncated_at_budget`` /
  ``capitulated`` outcome classes).

Generator-backed scenarios ship solver-verified instances (every instance carries its exact ceiling, floor,
and hidden solution) and exact scorers. Further scenarios follow the same pattern: subclass
``interlens.arena.Scenario``. ``SCENARIOS`` maps every bundled scenario name to a zero-argument factory
(the distributed long-context entries bind their task adapter).
"""

from .coding import CodingCollab
from .dlc import dlc_scenario
from .longcontext import DistributedLongContext, TaskAdapter
from .negotiation import Negotiation
from .relay import InfoRelay
from .security import SecurityDilemma

SCENARIOS = {s.name: s for s in (Negotiation, InfoRelay, SecurityDilemma, CodingCollab)}
SCENARIOS.update({
	"dlc_sniah": lambda: dlc_scenario("sniah"),
	"dlc_oolong_pairs": lambda: dlc_scenario("oolong_pairs"),
	"dlc_oolong_pairs32": lambda: dlc_scenario("oolong_pairs", name="dlc_oolong_pairs32"),
	"dlc_codeqa": lambda: dlc_scenario("codeqa"),
	"dlc_bcp": lambda: dlc_scenario("bcp"),
})

__all__ = ["Negotiation", "InfoRelay", "SecurityDilemma", "CodingCollab",
           "DistributedLongContext", "TaskAdapter", "dlc_scenario", "SCENARIOS"]
