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

"""Bundled scenarios: multi-issue negotiation and the wrong-shard info relay.

Both ship with solver-verified instance generators (exact enumeration — every instance carries its exact
ceiling, floor, and hidden optimum), exact scorers, and situational-sweep config. Further scenarios follow the
same pattern: subclass ``interlens.arena.Scenario``.
"""

from .negotiation import Negotiation
from .relay import InfoRelay

SCENARIOS = {s.name: s for s in (Negotiation, InfoRelay)}

__all__ = ["Negotiation", "InfoRelay", "SCENARIOS"]
