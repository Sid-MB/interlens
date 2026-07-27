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

# [rational_agents restructure: phase-C] 2026-07-24 — moved up from experiments/rational_agents/analysis/:
# negotiation-generic measurement, reusable by any experiment over this game family.
# (arena.negotiation.solutions); this module keeps only the Pareto/dominance/distance primitives.
"""Pure surplus-vector math: Pareto geometry, dominance, and distances.

Every function operates on a *surplus vector* ``x = (x_i)`` in surplus units ``x_i = u_i(deal) - tau_i`` — the
scale-invariant analysis object across parties with private point scales.

The **welfare and inequality scalars** (``utilitarian_welfare``/``egalitarian_welfare``/``nash_welfare``/
``nash_welfare_geomean``/``gini``) are re-exported from interlens' ``arena.negotiation.solutions``, which is
their one home: the scenario scores each episode's outcome with the same functions this layer aggregates, so a
run's reported welfare and the frontier it is compared against cannot drift apart. The names here are the local
aliases ``metrics.py``/``taxonomy.py`` already use.

The axiomatic solution points (NBS/KS/MNW and the frontier) come from ``solutions.py`` via ``game_analysis.py``;
the Pareto helpers below (``pareto_frontier``, ``dominating_alternatives``) are the small domination primitives
the metrics need (dominated-proposal detection) plus a fixture fallback, not a re-implementation of those.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from ..solutions import (egalitarian_welfare, gini, nash_welfare,  # noqa: F401
                                                   nash_geomean as nash_welfare_geomean,
                                                   welfare as utilitarian_welfare)

Vec = Sequence[float]


# --------------------------------------------------------------------- dominance / Pareto --
def dominates(y: Vec, x: Vec, *, strict_any: bool = True) -> bool:
	"""``y`` Pareto-dominates ``x``: ``y_i >= x_i`` for all i and (if ``strict_any``) strictly greater for at
	least one i. With ``strict_any=False`` this is weak dominance (``y_i >= x_i`` for all i)."""
	ge_all = all(float(yi) >= float(xi) for yi, xi in zip(y, x))
	if not ge_all:
		return False
	if not strict_any:
		return True
	return any(float(yi) > float(xi) for yi, xi in zip(y, x))


def dominating_alternatives(x: Vec, candidates: Sequence[Vec]) -> list[Vec]:
	"""Every candidate surplus vector that Pareto-dominates ``x``. Used to flag a *dominated proposal*: a party
	proposed/accepted ``x`` when some other feasible deal made everyone at least as well off and someone
	better (a left-on-the-table Pareto improvement)."""
	return [c for c in candidates if dominates(c, x)]


def pareto_frontier(surplus_vectors: Sequence[Vec]) -> list[tuple[float, ...]]:
	"""The non-dominated subset of a set of surplus vectors (the discrete Pareto frontier).

	O(|S|^2) brute force, exact at our enumerable deal-space scale (|D| ~ 243–3125, DESIGN.md §2). This is a
	fallback/utility for fixtures and audits — production frontiers are read from the precomputed
	``Instance.solution``."""
	pts = [tuple(float(v) for v in s) for s in surplus_vectors]
	front: list[tuple[float, ...]] = []
	for i, p in enumerate(pts):
		if any(j != i and dominates(q, p, strict_any=True) for j, q in enumerate(pts)):
			continue
		if p not in front:  # dedupe identical vectors
			front.append(p)
	return front


# ------------------------------------------------------------------------- distances --
def _scaled(x: Vec, scale: Vec | None) -> list[float]:
	if scale is None:
		return [float(v) for v in x]
	return [float(v) / s if s else 0.0 for v, s in zip(x, scale)]


def euclidean(x: Vec, y: Vec, *, scale: Vec | None = None) -> float:
	"""Euclidean distance ``||x - y||`` in surplus space, optionally after dividing each coordinate by a
	per-party ``scale`` (e.g. that party's max feasible surplus) so parties on different point scales are
	commensurable. With ``scale=None`` distances are in raw surplus units."""
	xs, ys = _scaled(x, scale), _scaled(y, scale)
	return math.sqrt(sum((a - b) ** 2 for a, b in zip(xs, ys)))


def distance_to_set(x: Vec, points: Sequence[Vec], *, scale: Vec | None = None) -> float:
	"""Minimum Euclidean distance from ``x`` to any vector in ``points`` (0 if ``x`` is one of them). Used for
	distance-to-Pareto-frontier: how far the realized outcome sits from the efficient set."""
	if not points:
		return float("nan")
	return min(euclidean(x, p, scale=scale) for p in points)
