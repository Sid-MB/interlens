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

# [rational_agents: fairness-arms] 2026-08-07
"""The **table objective**: one number per deal saying how good that deal is *for the whole table*.

This is the drop-in replacement for the per-seat surplus column ``tables.surplus[:, seat]`` that every
self-interested oracle in this package maximizes. Substituting it turns the existing best-response /
optimal-stopping stack into a fairness-seeking negotiator without touching a line of the recursion: the
proposal argmax, the reservation curve and the vote comparison all keep their shape and only change units.

The objective is :func:`mnw_objective` — a scalar flattening of Maximum Nash Welfare's two-stage rule
[caragiannis2019] over the **normalized** surplus vector:

    z_i(d) = clip(u_i(d) - tau_i, 0) / b_i          # b_i = party i's best surplus over the IR set
    k(d)   = #{i : u_i(d) - tau_i > 0}              # how many parties the deal actually satisfies
    obj(d) = k(d)/n  +  geomean_{i in S(d)} z_i(d) / n

The normalization by ``b_i`` is what makes this comparable across parties holding arbitrary private point
scales, and it is the same coordinate as the analysis layer's ``normalized_nash_welfare`` (whose ``game.scale``
is likewise the per-party max surplus over the IR set), so a policy's objective and the metric it is judged on
are the same quantity rather than two things that can drift apart.

**Why the flattening, and what it buys.** On the region that matters — deals where every party clears its
threshold — ``k(d) = n`` and ``obj(d) = 1 + NNW(d)/n``, so the ordering is *exactly* the normalized-Nash-welfare
ordering and ``argmax obj`` is the discrete NBS point. Off that region raw NNW is identically zero and gives a
maximizer nothing to steer by, whereas the flattening keeps ranking deals by how many parties they satisfy and
then by the product over those parties. The coalition term dominates by construction (``geomean z <= 1`` so the
whole second term is ``<= 1/n``, the width of one step in ``k/n``), which is precisely MNW's lexicographic
"satisfy the largest coalition first" rule. Hence :func:`max_objective_index` agrees with
``solutions.nash_bargaining_index`` whenever the strict-IR set is non-empty and with
``solutions.max_nash_welfare_index`` when it is not — pinned by property tests.

**Units.** ``obj`` lies in ``[0, 1 + 1/n]``, and no-deal scores ``0`` — the same convention as own-surplus
(where no-deal is also 0), which is what lets the optimal-stopping recursion in ``acceptance.py`` be reused
verbatim: its ``v_0 = 0`` base case still means "the value of never agreeing".

**Private information.** :func:`expected_objective` computes the same quantity when the opponents' sheets are
unknown, substituting each opponent's *posterior-expected* normalized surplus (from
:meth:`~interlens.arena.negotiation.beliefs.BeliefState.expected_normalized_surplus_matrix`) for the exact one.
This is a plug-in / mean-field estimate ``obj(E[z])`` rather than the true ``E[obj(z)]``; the two differ by a
Jensen gap and the plug-in is the optimistic side, because the geometric mean is concave. That bias is the
point of the ``fairness-rational`` vs ``fairness-oracle`` contrast rather than a defect to be hidden.
"""
from __future__ import annotations

import numpy as np

from .oracle_context import GameTables

#: Surpluses within this of zero are treated as "not strictly satisfied" when counting the coalition, so a
#: party sitting exactly on its threshold does not flicker in and out of ``k(d)`` on floating-point noise.
_EPS = 1e-12


def normalized_surplus_matrix(tables: GameTables) -> np.ndarray:
    """Per-deal per-party normalized surplus ``z`` of shape ``(|D|, n)``: ``clip(surplus, 0) / b_i``.

    ``b_i`` is party ``i``'s largest surplus over the **individually rational** set (every party at or above
    threshold) — the scale-invariant unit the whole fairness objective is expressed in, and the same
    ``game.scale`` the analysis layer's ``normalized_nash_welfare`` divides by. Falls back to the max over all
    deals when no deal is individually rational for everyone, and to ``1.0`` for a party whose best surplus is
    non-positive (it can never be made better off, so dividing by its "ideal" is meaningless). Below-threshold
    surpluses clip to 0 rather than going negative: they are not partial progress, they are unacceptable.

    Values can exceed ``1`` *outside* the IR set — ``b_i`` is the best party ``i`` can do in a deal everyone
    could sign, and a deal that tramples somebody else may pay ``i`` more than that. :func:`objective_from_normalized`
    caps at 1 for exactly this reason; see its docstring.

    Parameters
    ----------
    tables : GameTables
        Precomputed dense game tables. Only ``surplus`` is read, so this works on any table whose surplus
        column is populated for the parties in question.
    """
    X = np.asarray(tables.surplus, dtype=float)
    ir = np.all(X >= 0.0, axis=1)
    b = X[ir].max(axis=0) if bool(ir.any()) else X.max(axis=0)
    return np.clip(X, 0.0, None) / np.where(b > 0.0, b, 1.0)


def objective_from_normalized(z: np.ndarray) -> np.ndarray:
    """The table objective of shape ``(|D|,)`` from a normalized-surplus matrix ``z`` of shape ``(|D|, n)``.

    ``obj = k/n + geomean_{i in S} z_i / n`` with ``S`` the strictly-satisfied set and ``k = |S|`` (see the
    module docstring for why the two terms compose into MNW's lexicographic rule). A deal satisfying nobody
    scores exactly ``0``, matching the no-deal payoff. The geometric mean is taken in log space because a
    five- or six-party product of small normalized gains underflows well before the mean does.

    ``z`` is **capped at 1** first, and the cap is load-bearing rather than hygiene. The coalition term only
    dominates the welfare term if the latter cannot exceed ``1/n``, and a party can beat its IR-set ideal on a
    deal that leaves somebody else below threshold — uncapped, such a deal can outscore one that satisfies
    everybody, which would break both the lexicographic rule and the identity with the Nash Bargaining
    Solution. The cap is inert on the IR set (where ``z <= 1`` by construction), so it costs nothing where the
    objective is actually operating; it only refuses to reward paying one party out of another's threshold.

    Split out from :func:`mnw_objective` so the private-information path can feed it *expected* normalized
    surpluses through :func:`expected_objective` without re-deriving the flattening rule.
    """
    z = np.clip(np.asarray(z, dtype=float), 0.0, 1.0)
    n = z.shape[1]
    sat = z > _EPS
    k = sat.sum(axis=1)
    logs = np.where(sat, np.log(np.where(sat, z, 1.0)), 0.0)
    # geometric mean over the satisfied parties only; a deal satisfying nobody contributes no second term.
    geo = np.where(k > 0, np.exp(logs.sum(axis=1) / np.maximum(k, 1)), 0.0)
    return k / n + geo / n


def mnw_objective(tables: GameTables) -> np.ndarray:
    """The full-information table objective of shape ``(|D|,)`` — what the **fairness oracle** maximizes.

    Composition of :func:`normalized_surplus_matrix` and :func:`objective_from_normalized`. Its argmax is the
    discrete NBS deal when some deal clears every threshold, and the Maximum-Nash-Welfare deal otherwise.
    """
    return objective_from_normalized(normalized_surplus_matrix(tables))


def expected_objective(tables: GameTables, seat: int, expected_z: dict[int, np.ndarray]) -> np.ndarray:
    """The table objective under a posterior over the other seats' hidden sheets — what the **fairness
    algorithmic** agent maximizes.

    The acting seat's own column is exact (it holds its own sheet, so its normalized surplus is known); every
    other seat's column is the posterior-expected normalized surplus supplied in ``expected_z``. Any seat
    missing from ``expected_z`` and not the acting seat is treated as fully satisfied (``z = 1``), which is the
    only neutral choice: scoring it 0 would make every deal look like it satisfies nobody and would collapse
    the objective to a constant.

    Parameters
    ----------
    tables : GameTables
        Tables whose ``surplus`` column for ``seat`` is populated. Under private information the other columns
        are padding (the caller's ``_tables`` fills them with zeros) and are deliberately never read here.
    seat : int
        The acting seat, whose own normalized surplus is computed exactly from its own sheet.
    expected_z : dict[int, np.ndarray]
        ``{opponent_seat: (|D|,) posterior-expected normalized surplus}``, e.g. from
        :meth:`~interlens.arena.negotiation.beliefs.BeliefState.expected_normalized_surplus_matrix`.

    Returns the ``(|D|,)`` expected objective. See the module docstring on the plug-in (Jensen) bias.

    One further deviation from the full-information case, forced by the information condition: the acting
    seat's normalizer is its best surplus over ALL deals, not over the IR set, because identifying the IR set
    requires the thresholds it does not have. This cannot move the ranking within its own column (a positive
    constant), but it does shift how its own gains trade against the opponents' in the geometric mean.
    """
    X = np.asarray(tables.surplus, dtype=float)
    own = X[:, int(seat)]
    b_own = float(own.max())
    z = np.ones((X.shape[0], X.shape[1]), dtype=float)
    z[:, int(seat)] = np.clip(own, 0.0, None) / (b_own if b_own > 0.0 else 1.0)
    for opp, col in expected_z.items():
        z[:, int(opp)] = np.clip(np.asarray(col, dtype=float), 0.0, None)
    return objective_from_normalized(z)


def max_objective_index(objective: np.ndarray) -> int:
    """The objective-maximizing deal row, ties broken by lowest index so a policy built on this is
    deterministic — the same canonical tie-break ``solutions._argmax_ties`` and ``np.argmax`` use."""
    return int(np.argmax(np.asarray(objective, dtype=float)))
