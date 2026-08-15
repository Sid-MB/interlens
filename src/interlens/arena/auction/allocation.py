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
#
# [implement: auctions | 2026-08-15 | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""Bundle values, the exact efficient allocation, and the payment rules.

Everything here is a pure function of one stage's realized numbers, wrapped in :class:`ValueModel` so the six
arrays that define a stage's allocation problem travel together.

The bundle-value function is design.md §2.2 exactly::

    V_i(S) = sum_{j in S, rank r}  v_ij * d_i^(r-1)          # substitutes: diminishing returns
           + c_i * 1[S superset-of-or-equal T_i] * sum_{j in T_i} v_ij    # complements on the private target
    V_i(S) = -inf  if |S| > k_i                              # capacity

**The efficient allocation is solved EXACTLY, not heuristically**, because every efficiency and suppression
number in the campaign divides by it. Two structural facts make exactness cheap:

1. Without synergies, the problem is an assignment problem — expand bidder ``i`` into ``k_i`` ranked slots
   whose ``r``-th slot pays ``v_ij * d_i^(r-1)``, add one zero-valued "unsold" slot per item, and solve it
   with the Hungarian method [kuhn1955]. The rank multipliers are decreasing, so the solver automatically
   pairs a bidder's highest-valued items with its lowest ranks, which is precisely the sorted form of the
   bundle-value formula (rearrangement inequality). No approximation enters.
2. Synergies are an all-or-nothing bonus on ONE target set per bidder, so enumerating the ``2^n_bidders``
   subsets of bidders whose synergy is active — forcing each active bidder's target items to it and adding
   the bonus — covers every allocation exactly once at its true value. The optimum over the enumeration is
   therefore the true optimum (each case is a valid lower bound and the optimum's own activation pattern is
   one of the cases).

Payments: :func:`vcg_payments` is the Clarke-Groves pivot rule [clarke1971_groves1973],
:func:`clinching_prices` the Ausubel ascending rule [ausubel2004, pp. 1454-1460], :func:`uniform_price_clear`
the highest-rejected-bid rule, and :func:`sealed_single_outcome` the one-lot first/second-price settlement.
The exact per-stage EQUILIBRIUM benchmarks that suppression divides against live in :mod:`.benchmarks`.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

#: Finite penalty standing in for "this cell is forbidden" inside the assignment solver. Finite rather than
#: ``inf`` so the primal-dual potentials stay arithmetic; large enough that no real allocation can beat one.
_FORBIDDEN = -1e12


# --------------------------------------------------------------------------------------------------------- #
# The assignment solver.
# --------------------------------------------------------------------------------------------------------- #
def _min_cost_assignment(cost: np.ndarray) -> np.ndarray:
    """Exact minimum-cost assignment of every ROW to a distinct column, ``n_rows <= n_cols``.

    The O(n^2 m) primal-dual shortest-augmenting-path form of the Hungarian method [kuhn1955], with the inner
    scan over columns vectorized. Returns the column index chosen for each row. Implemented here rather than
    imported because interlens does not depend on SciPy."""
    cost = np.asarray(cost, dtype=float)
    n, m = cost.shape
    if n > m:
        raise ValueError(f"assignment needs n_rows <= n_cols, got {n} x {m}")
    INF = np.inf
    u = np.zeros(n + 1)
    v = np.zeros(m + 1)
    p = np.zeros(m + 1, dtype=int)      # p[j] = row matched to column j (1-indexed; 0 = free)
    way = np.zeros(m + 1, dtype=int)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = np.full(m + 1, INF)
        used = np.zeros(m + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]
            cur = cost[i0 - 1] - u[i0] - v[1:]
            free = ~used[1:]
            better = free & (cur < minv[1:])
            minv[1:][better] = cur[better]
            way[1:][better] = j0
            masked = np.where(free, minv[1:], INF)
            j1 = int(np.argmin(masked)) + 1
            delta = float(masked[j1 - 1])
            np.add.at(u, p[used], delta)
            v[used] -= delta
            minv[~used] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    out = np.full(n, -1, dtype=int)
    for j in range(1, m + 1):
        if p[j] > 0:
            out[p[j] - 1] = j - 1
    return out


def max_weight_assignment(value: np.ndarray) -> tuple[np.ndarray, float]:
    """Maximum-weight assignment of rows to distinct columns: ``(column_per_row, total_value)``. The
    maximization face of :func:`_min_cost_assignment` (it negates the matrix)."""
    cols = _min_cost_assignment(-np.asarray(value, dtype=float))
    total = float(sum(value[r, c] for r, c in enumerate(cols)))
    return cols, total


# --------------------------------------------------------------------------------------------------------- #
# Allocations.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Allocation:
    """Who won each lot. ``winner_of[j]`` is the seat index that won lot ``j``, or ``None`` if it went
    unsold. The canonical allocation object every welfare, payment, and metric function consumes."""

    winner_of: tuple[int | None, ...]

    @property
    def n_items(self) -> int:
        """Number of lots this allocation covers."""
        return len(self.winner_of)

    def bundle(self, seat: int) -> tuple[int, ...]:
        """The lots won by ``seat``, in slot order."""
        return tuple(j for j, w in enumerate(self.winner_of) if w == seat)

    def winners(self) -> tuple[int, ...]:
        """Seats that won at least one lot, ascending."""
        return tuple(sorted({w for w in self.winner_of if w is not None}))

    def to_json(self) -> dict:
        """JSON-ready dict."""
        return {"winner_of": list(self.winner_of)}

    @staticmethod
    def from_json(d: dict) -> "Allocation":
        """Rebuild an :class:`Allocation` from :meth:`to_json` output."""
        return Allocation(tuple(None if w is None else int(w) for w in d["winner_of"]))

    @staticmethod
    def empty(n_items: int) -> "Allocation":
        """The all-unsold allocation (welfare 0) — what a stage with no sale scores, never "excluded"
        (design.md §5.1)."""
        return Allocation(tuple([None] * n_items))


@dataclass(frozen=True)
class ValueModel:
    """One stage's allocation problem: the realized value table plus every structural parameter the bundle
    value depends on.

    Parameters
    ----------
    values : np.ndarray
        ``(n_bidders, n_items)`` realized whole-number valuations ``v_ij``.
    capacities : tuple[int, ...]
        Per-seat maximum number of lots ``k_i``.
    decays : tuple[float, ...]
        Per-seat diminishing-returns factor ``d_i`` in ``(0, 1]``.
    synergy_rates : tuple[float, ...]
        Per-seat complementarity rate ``c_i`` (public).
    synergy_targets : tuple[tuple[int, ...] | None, ...]
        Per-seat private target SET (``None`` when the seat has no synergy).
    budgets : tuple[int, ...] | None
        Per-seat whole-number stage budget, used by :meth:`budget_feasible` and the payment collectability
        checks. It does NOT enter :meth:`efficient_allocation`: a budget binds on PAYMENTS, which depend on
        the mechanism, while the efficient allocation is a property of values alone. Design.md §5.1's
        "allocations respecting every capacity and budget" is therefore implemented as a capacity-exact
        optimum plus an explicit budget-feasibility report, rather than by folding a price-dependent
        constraint into a value-only optimization (a resolved design ambiguity).
    """

    values: np.ndarray
    capacities: tuple[int, ...]
    decays: tuple[float, ...]
    synergy_rates: tuple[float, ...]
    synergy_targets: tuple[tuple[int, ...] | None, ...]
    budgets: tuple[int, ...] | None = None

    @staticmethod
    def from_spec(spec, t: int) -> "ValueModel":
        """Build the value model for stage ``t`` (1-indexed) of an :class:`~.spec.AuctionSpec`."""
        st = spec.stage(t)
        return ValueModel(values=st.value_array, capacities=spec.capacities, decays=spec.decays,
                          synergy_rates=spec.synergy_rates, synergy_targets=st.synergy_target,
                          budgets=st.budgets)

    @property
    def n_bidders(self) -> int:
        """Number of seats."""
        return int(self.values.shape[0])

    @property
    def n_items(self) -> int:
        """Number of lots."""
        return int(self.values.shape[1])

    # -- bundle values -------------------------------------------------------------------------------------
    def bundle_value(self, seat: int, bundle) -> float:
        """``V_i(S)`` per design.md §2.2: decayed sum over the bundle sorted descending, plus the synergy
        bonus when the bundle CONTAINS the private target set, and ``-inf`` when capacity is exceeded."""
        items = tuple(bundle)
        if len(items) > self.capacities[seat]:
            return float("-inf")
        if not items:
            return 0.0
        vals = np.sort(self.values[seat, list(items)].astype(float))[::-1]
        d = float(self.decays[seat])
        total = float(np.dot(vals, d ** np.arange(len(vals))))
        target = self.synergy_targets[seat]
        if target is not None and self.synergy_rates[seat] and set(target).issubset(items):
            total += float(self.synergy_rates[seat]) * float(self.values[seat, list(target)].sum())
        return total

    def welfare(self, alloc: Allocation) -> float:
        """Realized welfare of an allocation: the sum of every winner's bundle value."""
        return float(sum(self.bundle_value(i, alloc.bundle(i)) for i in alloc.winners()))

    def budget_feasible(self, alloc: Allocation, payments) -> bool:
        """Whether every winner can pay its assigned payment out of its stage budget. ``True`` when the model
        carries no budgets."""
        if self.budgets is None:
            return True
        return all(float(payments[i]) <= float(self.budgets[i]) + 1e-9 for i in range(self.n_bidders))

    # -- the exact optimum ---------------------------------------------------------------------------------
    def _assignment_value_matrix(self, active: tuple[int, ...]) -> tuple[np.ndarray, list[tuple[int, int]]]:
        """The ``(n_items, n_slots)`` value matrix for one synergy-activation pattern, and the slot legend.

        Columns are ``(seat, rank)`` capacity slots followed by ``n_items`` unsold slots (``seat = -1``).
        A slot's value is ``v_ij * d_i^rank``. For every seat in ``active`` its target items are forbidden
        everywhere except that seat's own slots (and forbidden from going unsold), which is what "this seat's
        synergy fires" means as a constraint."""
        legend: list[tuple[int, int]] = []
        cols = []
        for i in range(self.n_bidders):
            d = float(self.decays[i])
            for r in range(int(self.capacities[i])):
                legend.append((i, r))
                cols.append(self.values[i].astype(float) * (d ** r))
        for _ in range(self.n_items):
            legend.append((-1, 0))
            cols.append(np.zeros(self.n_items))
        mat = np.stack(cols, axis=1)                       # (n_items, n_slots)
        for i in active:
            target = self.synergy_targets[i] or ()
            own = [c for c, (s, _) in enumerate(legend) if s == i]
            for j in target:
                mask = np.full(mat.shape[1], _FORBIDDEN)
                mask[own] = 0.0
                mat[j] = np.where(mask == 0.0, mat[j], _FORBIDDEN)
        return mat, legend

    def efficient_allocation(self) -> tuple[Allocation, float]:
        """The welfare-maximizing allocation and its welfare, solved EXACTLY.

        Enumerates the subsets of synergy-capable seats whose target set is fully awarded (skipping patterns
        whose targets overlap or exceed a capacity), solves each as a maximum-weight assignment over ranked
        capacity slots plus unsold slots, adds the activation bonuses, and takes the best. Ties are broken by
        the enumeration order (empty activation first, then ascending seat subsets), so the result is
        deterministic — which the S1 uniqueness screen depends on."""
        capable = tuple(i for i in range(self.n_bidders)
                        if self.synergy_targets[i] is not None and self.synergy_rates[i]
                        and len(self.synergy_targets[i]) <= self.capacities[i])
        best_alloc, best_welfare = Allocation.empty(self.n_items), 0.0
        for size in range(len(capable) + 1):
            for active in combinations(capable, size):
                seen: set[int] = set()
                overlap = False
                for i in active:
                    tgt = set(self.synergy_targets[i])
                    if tgt & seen:
                        overlap = True
                        break
                    seen |= tgt
                if overlap:
                    continue
                mat, legend = self._assignment_value_matrix(active)
                cols, _ = max_weight_assignment(mat)
                winner_of = tuple(legend[c][0] if legend[c][0] >= 0 else None for c in cols)
                if any(mat[j, c] <= _FORBIDDEN / 2 for j, c in enumerate(cols)):
                    continue                                # the forced pattern is infeasible
                alloc = Allocation(winner_of)
                w = self.welfare(alloc)                     # scored by the TRUE bundle value, not the matrix
                if w > best_welfare + 1e-9:
                    best_alloc, best_welfare = alloc, w
        return best_alloc, best_welfare

    def max_welfare(self) -> float:
        """Welfare of the efficient allocation — the denominator of ``efficiency_t`` (design.md §5.1)."""
        return self.efficient_allocation()[1]

    def welfare_without(self, seat: int) -> float:
        """Maximum welfare of the OTHER seats when ``seat`` is absent — the counterfactual the VCG pivot
        payment charges."""
        keep = [i for i in range(self.n_bidders) if i != seat]
        sub = ValueModel(values=self.values[keep], capacities=tuple(self.capacities[i] for i in keep),
                         decays=tuple(self.decays[i] for i in keep),
                         synergy_rates=tuple(self.synergy_rates[i] for i in keep),
                         synergy_targets=tuple(self.synergy_targets[i] for i in keep),
                         budgets=None)
        return sub.max_welfare()


def brute_force_allocation(vm: ValueModel) -> tuple[Allocation, float]:
    """The exhaustive optimum over every assignment of items to seats-or-unsold. Exponential
    (``(n+1)^n_items``) and used ONLY to verify :meth:`ValueModel.efficient_allocation` in the tests — the
    exactness claim is what every efficiency number rests on, so it is checked rather than asserted."""
    n, m = vm.n_bidders, vm.n_items
    best, best_w = Allocation.empty(m), 0.0
    for combo in np.ndindex(*([n + 1] * m)):
        alloc = Allocation(tuple(None if c == n else int(c) for c in combo))
        w = vm.welfare(alloc)
        if w > best_w + 1e-9:
            best, best_w = alloc, w
    return best, best_w


# --------------------------------------------------------------------------------------------------------- #
# Payment rules.
# --------------------------------------------------------------------------------------------------------- #
def vcg_payments(vm: ValueModel, alloc: Allocation | None = None) -> tuple[np.ndarray, Allocation]:
    """Clarke-Groves pivot payments for a multi-item allocation [clarke1971_groves1973].

    ``p_i = W_{-i} - (W - V_i(S_i))``: the welfare the others would have obtained without ``i``, minus the
    welfare they actually obtain. A seat that wins nothing pays 0, and no payment exceeds the winner's own
    bundle value. ``alloc`` defaults to the efficient allocation (the only allocation for which the pivot rule
    is incentive compatible); passing a different one prices THAT allocation under the same rule, which is how
    the clinching benchmark is cross-checked.

    Returns ``(payments, alloc)`` with ``payments`` a ``(n_bidders,)`` float array."""
    if alloc is None:
        alloc, welfare = vm.efficient_allocation()
    else:
        welfare = vm.welfare(alloc)
    pay = np.zeros(vm.n_bidders)
    for i in range(vm.n_bidders):
        own = vm.bundle_value(i, alloc.bundle(i))
        if not alloc.bundle(i):
            continue
        pay[i] = vm.welfare_without(i) - (welfare - own)
    return pay, alloc


def sealed_single_outcome(bids, *, pricing: str, tie_break, reserve: int = 0
                          ) -> tuple[int | None, int]:
    """Settle a ONE-lot sealed auction: ``(winner_seat_or_None, price)``.

    The highest bid at or above ``reserve`` wins; ties are resolved by position in ``tie_break`` (the stage's
    seeded seat permutation, announced before bidding). Under ``"second_price"`` the winner pays the
    second-highest bid floored at the reserve [vickrey1961]; under ``"first_price"`` it pays its own bid. A
    bid of ``None`` is a seat that took no priced action and is excluded from both the win and the price."""
    live = [(int(b), s) for s, b in enumerate(bids) if b is not None and int(b) >= reserve]
    if not live:
        return None, 0
    order = {s: k for k, s in enumerate(tie_break)}
    top = max(b for b, _ in live)
    winner = min((s for b, s in live if b == top), key=lambda s: order[s])
    if pricing == "first_price":
        return winner, top
    others = [b for b, s in live if s != winner]
    return winner, max(reserve, max(others)) if others else reserve


def uniform_price_clear(schedules, *, supply: int, tie_break, reserve: int = 0
                        ) -> tuple[np.ndarray, int]:
    """Clear a uniform-price sale of ``supply`` identical units: ``(units_won_per_bidder, clearing_price)``.

    ``schedules[i]`` is bidder ``i``'s weakly-decreasing per-unit bid vector. All unit bids at or above
    ``reserve`` are pooled and ranked; the top ``supply`` win, and every winner pays the HIGHEST REJECTED bid
    per unit (the reserve when nothing is rejected). Ties at the margin are resolved by position in
    ``tie_break``. Shading the inframarginal units to move this price down is exactly the demand reduction of
    [ausubel_cramton2014, pp. 1370-1378]."""
    order = {s: k for k, s in enumerate(tie_break)}
    pool = [(int(b), order[i], i) for i, sched in enumerate(schedules) for b in sched if int(b) >= reserve]
    pool.sort(key=lambda t: (-t[0], t[1]))
    n = len(schedules)
    units = np.zeros(n, dtype=int)
    for b, _, i in pool[:supply]:
        units[i] += 1
    rejected = pool[supply:]
    price = int(rejected[0][0]) if rejected else int(reserve)
    return units, max(price, int(reserve))


def clinching_prices(schedules, *, supply: int, increment: int = 1, reserve: int = 0
                     ) -> tuple[np.ndarray, np.ndarray]:
    """Run the Ausubel ascending clock on ``supply`` identical units [ausubel2004, pp. 1454-1460].

    ``schedules[i]`` is bidder ``i``'s weakly-decreasing per-unit marginal value/bid vector; its demand at
    clock price ``p`` is the number of entries worth STRICTLY MORE than ``p`` (a bidder willing to pay ``v``
    leaves as the clock passes ``v``). The strictness is what makes the discrete clock reproduce the Vickrey
    payment exactly rather than overcharging by one increment, which the tests check against a hand-computed
    example. Whenever residual rival demand falls below supply, bidder ``i`` CLINCHES the shortfall at the
    current clock price, and the clock keeps rising until aggregate demand no longer exceeds supply. Returns
    ``(units_won, total_payment)``.

    The point of the rule is that the price a bidder pays for a unit is set by the moment its rivals' demand
    receded, not by its own later bidding — which is why truthful demand is an equilibrium and the
    demand-reduction incentive of the uniform-price rule disappears."""
    n = len(schedules)
    sched = [sorted((int(b) for b in s), reverse=True) for s in schedules]
    units = np.zeros(n, dtype=int)
    pay = np.zeros(n, dtype=float)
    top = max((s[0] for s in sched if s), default=int(reserve))
    p = int(reserve)
    while True:
        demand = np.array([sum(1 for b in sched[i] if b > p) for i in range(n)], dtype=int)
        total = int(demand.sum())
        for i in range(n):
            clinched = min(int(demand[i]), max(0, supply - (total - int(demand[i]))))
            if clinched > units[i]:
                pay[i] += (clinched - int(units[i])) * p
                units[i] = clinched
        if total <= supply or p > top:
            break
        p += increment
    return units, pay
