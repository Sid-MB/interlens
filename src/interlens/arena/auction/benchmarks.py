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

"""The exact per-stage equilibrium benchmarks every suppression metric divides against (design.md §4.3, §5).

A :class:`Benchmark` is the answer to "what would this stage have looked like if everyone played the
format's risk-neutral equilibrium against the REALIZED draws" — a bid for every seat and lot, the resulting
allocation, prices, revenue, and welfare. Suppression is then ``(benchmark_bid - realized_bid) / own_value``,
so a wrong benchmark silently rescales the campaign's headline; every benchmark here is therefore either a
closed-form result with its citation and page range, or an explicitly simulated fixed point, and each is
unit-tested against a hand-computed case.

One entry point, :func:`stage_benchmark`, dispatches on the mechanism — benchmarks are configs of one
function for exactly the reason formats are configs of one runner.

The five benchmarks:

- **second-price / English** — bid your own value; weakly dominant under private values, IPV and APV alike
  [vickrey1961, pp. 20-23]. Under INTERDEP the value is not known, so the benchmark is the expectation
  conditional on winning (:func:`expected_value_given_winning`), which is what makes a shortfall a winner's
  curse rather than an arithmetic error [kagel_levin1986].
- **Dutch / first-price** — the risk-neutral Nash equilibrium. Under IPV with symmetric bidders that is the
  closed form ``(n-1)/n * v`` [riley_samuelson1981, pp. 383-385]; under APV the asymmetric fixed point is
  solved numerically on the integer bid grid by :func:`solve_rnne_bids`.
- **SAA** — the competitive outcome of straightforward bidding, simulated exactly [milgrom2000, pp. 250-258].
- **uniform price** — the demand-reduction-FREE schedule (true decayed marginal values), against which the
  demand-reduction gradient of [ausubel_cramton2014, pp. 1370-1378] is measured.
- **clinching** — truthful demand, which is an equilibrium of the Ausubel rule [ausubel2004].
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from .allocation import (Allocation, ValueModel, clinching_prices, sealed_single_outcome,
                         uniform_price_clear)


@dataclass(frozen=True)
class Benchmark:
    """One stage's equilibrium reference outcome.

    Attributes
    ----------
    label : str
        Short name of the benchmark (``"truthful"``, ``"rnne"``, ``"straightforward"``, ...).
    citation_key : str
        Key into :data:`~interlens.arena.auction.references.REFERENCES` for the result this implements.
    bids : np.ndarray
        ``(n_bidders, n_items)`` equilibrium bid per seat and lot; ``nan`` where the benchmark prescribes no
        priced action. This is the numerator side of every suppression measurement.
    alloc : Allocation
        Who wins under the benchmark bids.
    prices : np.ndarray
        ``(n_items,)`` price paid per lot (0 where unsold).
    payments : np.ndarray
        ``(n_bidders,)`` total payment per seat.
    welfare : float
        Realized welfare of ``alloc`` under the true values.
    revenue : float
        Total payments.
    note : str
        What the benchmark assumes, in one line — carried on the object so an analysis table can print the
        assumption beside the number instead of relying on the reader knowing it.
    detail : dict
        Anything format-specific (e.g. per-lot standing-price paths for SAA).
    """

    label: str
    citation_key: str
    bids: np.ndarray
    alloc: Allocation
    prices: np.ndarray
    payments: np.ndarray
    welfare: float
    revenue: float
    note: str = ""
    detail: dict = field(default_factory=dict)


# --------------------------------------------------------------------------------------------------------- #
# Second-price / English.
# --------------------------------------------------------------------------------------------------------- #
def truthful_benchmark(vm: ValueModel, *, tie_break, reserve: int = 0, pricing: str = "second_price",
                       bids: np.ndarray | None = None, budgets=None) -> Benchmark:
    """The dominant-strategy benchmark for a ONE-lot second-price (or English) stage: everyone bids its own
    value [vickrey1961, pp. 20-23].

    ``bids`` overrides the truthful bid vector — used by the INTERDEP path, where the benchmark bid is the
    conditional expectation rather than the (unknown) realized value.

    ``budgets`` caps each benchmark bid at what the seat can actually pay. Bidding above budget is a LEGALITY
    error in this harness (payments must be collectible, design.md §3.2), so ``min(value, budget)`` — not the
    value — is what an information-conditional rational bidder submits. Leaving the cap out scored a
    budget-bound seat's legal bid as shading: measured on the ``all_rational`` arm of the single-lot bank, the
    two budget-bound seats of five produced ``bid_value_ratio = 0.91`` and a spurious ``suppression = 0.108``
    in a cell where nothing was suppressed. The uncapped own-value vector is kept as ``detail["truthful_bids"]``
    and reported as the secondary column."""
    if vm.n_items != 1:
        raise ValueError("truthful_benchmark is the single-lot benchmark; use saa_benchmark for many lots")
    uncapped = vm.values[:, 0].astype(float) if bids is None else np.asarray(bids, dtype=float).reshape(-1)
    b = uncapped if budgets is None else np.minimum(uncapped, np.asarray(budgets, dtype=float).reshape(-1))
    winner, price = sealed_single_outcome([int(round(x)) for x in b], pricing=pricing,
                                          tie_break=tie_break, reserve=reserve)
    alloc = Allocation((winner,))
    payments = np.zeros(vm.n_bidders)
    if winner is not None:
        payments[winner] = price
    return Benchmark(label="truthful", citation_key="vickrey1961", bids=b.reshape(vm.n_bidders, 1),
                     alloc=alloc, prices=np.array([float(price) if winner is not None else 0.0]),
                     payments=payments, welfare=vm.welfare(alloc), revenue=float(payments.sum()),
                     note="bid = min(own value, budget), weakly dominant in a second-price/English "
                          "private-values stage subject to payments being collectible",
                     detail={"truthful_bids": uncapped.reshape(vm.n_bidders, 1)})


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via ``math.erf`` (interlens does not depend on SciPy)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def expected_value_given_winning(signal: int, *, private_part: float, gamma: float, sigma_nu: float,
                                 n_rivals: int, resale_grid) -> float:
    """``E[v_i | own signal, i has the highest signal]`` for the INTERDEP structure — the winner's-curse
    correction [kagel_levin1986, pp. 908-915].

    The unobserved common resale value ``R`` has the public prior ``resale_grid`` (the generator draws it
    uniformly on the catalogue base range). The seat's signal is ``s = round(R * exp(nu))`` with
    ``nu ~ N(0, sigma_nu^2)`` public, so the likelihood of the signal is lognormal around ``R``, and
    conditioning on WINNING multiplies in the probability that all ``n_rivals`` rival signals fall below
    ``s`` given ``R``. The returned value is ``private_part + gamma * E[R | ...]``, which is strictly below
    the naive ``private_part + gamma * signal`` whenever ``sigma_nu > 0`` and there is at least one rival —
    the shading that separates a sophisticated bidder from a cursed one."""
    grid = np.asarray(resale_grid, dtype=float)
    if sigma_nu <= 0 or signal <= 0:
        return float(private_part + gamma * signal)
    dev = (math.log(signal) - np.log(grid)) / sigma_nu
    like = np.exp(-0.5 * dev ** 2)
    win = np.array([_norm_cdf(float(d)) for d in dev]) ** n_rivals
    w = like * win
    if w.sum() <= 0:
        return float(private_part + gamma * signal)
    return float(private_part + gamma * float(np.dot(grid, w) / w.sum()))


# --------------------------------------------------------------------------------------------------------- #
# Dutch / first-price.
# --------------------------------------------------------------------------------------------------------- #
def rnne_shade(n_bidders: int) -> float:
    """The symmetric risk-neutral first-price shading factor ``(n-1)/n`` — ``0.8`` at the design's five seats
    [riley_samuelson1981, pp. 383-385]. Exact for uniformly distributed IPV values; the design scores Dutch
    claim prices against it (design.md §3.3)."""
    return (n_bidders - 1) / n_bidders


def rnne_symmetric_bid(value: float, n_bidders: int) -> float:
    """The symmetric-uniform-IPV first-price equilibrium bid ``(n-1)/n * v``."""
    return rnne_shade(n_bidders) * float(value)


def rival_max_cdf_curve(rival_pmfs, grid: np.ndarray) -> np.ndarray:
    """``G(x) = prod_k F_k(x)`` — the CDF of the highest RIVAL value — evaluated on ``grid``.

    Valid as a product because ``(z_k, eps_k)`` are independent across bidders (they are correlated only
    across slots within a bidder), which is the sense in which the APV structure is affiliated in values but
    not in types."""
    out = np.ones_like(grid, dtype=float)
    for values, probs in rival_pmfs:
        v = np.asarray(values, dtype=float)
        p = np.asarray(probs, dtype=float)
        p = p / p.sum()
        out *= np.array([float(p[v <= x].sum()) for x in grid])
    return out


def rnne_bid_against(value: float, rival_pmfs, *, lower: float = 0.0, n_grid: int = 400) -> float:
    """The risk-neutral first-price equilibrium bid for a bidder of type ``value`` facing rivals with the
    given value distributions [riley_samuelson1981, pp. 383-385]::

        b(v) = v - integral_{lower}^{v} G(x) dx / G(v),    G(x) = prod_k F_k(x)

    Solved numerically by trapezoid quadrature on a grid between ``lower`` and ``value``, so it applies to
    the design's lognormal-shaped value distributions with no closed form. It is the EXACT equilibrium when
    the bidders are symmetric — the test suite checks it reproduces ``(n-1)/n * v`` on the uniform case — and
    a monotone, well-defined one-step approximation when they are not (the exact asymmetric equilibrium is a
    boundary-value ODE system with no closed form, and iterated best response on the integer bid grid pools
    at the top rather than converging, so it is deliberately not used).

    ``G(v) = 0`` (a type below every rival's support, which can only lose) returns ``lower``."""
    v = float(value)
    if v <= lower:
        return float(lower)
    grid = np.linspace(lower, v, n_grid)
    G = rival_max_cdf_curve(rival_pmfs, grid)
    if G[-1] <= 0:
        return float(lower)
    return float(v - np.trapezoid(G, grid) / G[-1]) if hasattr(np, "trapezoid") else \
        float(v - np.trapz(G, grid) / G[-1])


# --------------------------------------------------------------------------------------------------------- #
# SAA.
# --------------------------------------------------------------------------------------------------------- #
def best_bundle_at_prices(vm: ValueModel, seat: int, prices: np.ndarray,
                          forced: tuple[int, ...] = ()) -> tuple[tuple[int, ...], float]:
    """The bundle maximizing ``V_i(S) - sum_{j in S} price_j`` subject to capacity, by exact enumeration over
    bundles of size at most ``k_i`` — straightforward bidding's demand correspondence [milgrom2000].

    ``forced`` items are held (the lots the seat is already standing high on, which it cannot walk away from
    within the stage). Ties break toward the SMALLER bundle and then the lexicographically first, so the
    simulation is deterministic.

    A seat's DEMAND is what makes this the information-conditional benchmark: a capacity-``k`` bidder facing 20
    lots demands at most ``k`` of them, so the lots outside its demand are lots a rational bidder places no
    priced action on -- not lots it suppressed."""
    k = int(vm.capacities[seat])
    items = [j for j in range(vm.n_items) if j not in forced]
    if forced:
        best = tuple(sorted(forced))
        best_surplus = vm.bundle_value(seat, best) - float(prices[list(best)].sum())
    else:
        best, best_surplus = (), 0.0
    for size in range(0, k - len(forced) + 1):
        for extra in combinations(items, size):
            bundle = tuple(sorted(forced + extra))
            surplus = vm.bundle_value(seat, bundle) - float(prices[list(bundle)].sum()) if bundle else 0.0
            if surplus > best_surplus + 1e-9:
                best, best_surplus = bundle, surplus
    return best, best_surplus


def saa_competitive_benchmark(vm: ValueModel, *, increment: int, reserve: int = 0, tie_break,
                              round_cap: int = 200) -> Benchmark:
    """Simulate the simultaneous ascending auction under STRAIGHTFORWARD bidding [milgrom2000, pp. 250-258].

    Every round, each seat computes its surplus-maximizing bundle at "prices to pay" (the standing price on
    lots it already holds, standing + ``increment`` on lots it does not) and bids ``standing + increment`` on
    any lot in that bundle it does not hold. The clock stops when a round passes with no new bid, or at
    ``round_cap``. The resulting standing prices are the competitive benchmark prices, and the resulting
    assignment is the competitive benchmark allocation.

    **The per-lot benchmark BID is information-conditional** (design.md v2.1 implementation notes, ratified
    2026-08-15): the seat's own value ``v_ij`` on the lots it ever DEMANDED in the simulation, and ``nan`` on
    the lots it never demanded. Under APV that is the change that makes suppression mean what the metric says
    it means. A capacity-2 bidder facing 20 lots rationally places no priced action on 18 of them; scoring
    those 18 cells against its own value -- which the previous all-lots truthful matrix did -- booked a
    capacity constraint as suppression and made ``all_rational`` read as a colluding arm. The full own-value
    matrix survives as ``detail["truthful_bids"]`` and is reported as the secondary suppression column, so both
    numbers are always visible."""
    n, m = vm.n_bidders, vm.n_items
    price = np.full(m, float(reserve))
    holder: list[int | None] = [None] * m
    order = {s: k for k, s in enumerate(tie_break)}
    demanded: list[set] = [set() for _ in range(n)]
    placed = np.full((n, m), np.nan)          # the highest amount each seat actually BID on each lot
    rounds = 0
    while rounds < round_cap:
        rounds += 1
        new_bids: dict[int, list[int]] = {}
        for i in sorted(range(n), key=lambda s: order[s]):
            pay = np.array([price[j] if holder[j] == i else price[j] + increment for j in range(m)])
            # The lots this seat is ALREADY standing high on are forced into its bundle: within a stage it
            # cannot walk away from a standing high bid. Omitting them let a capacity-3 seat holding three lots
            # demand three different ones and end the stage holding six, which made the benchmark allocation
            # infeasible and its welfare -inf -- invisible at a 5-round cap (nobody accumulates that fast) and
            # systematic at 20 rounds.
            held = tuple(j for j in range(m) if holder[j] == i)
            bundle, _ = best_bundle_at_prices(vm, i, pay, forced=held)
            demanded[i].update(bundle)
            want = [j for j in bundle if holder[j] != i]
            if want:
                new_bids[i] = want
        if not new_bids:
            break
        # Resolve simultaneous demands lot by lot; ties by the seeded permutation.
        for j in range(m):
            claimants = [i for i, lots in new_bids.items() if j in lots]
            if not claimants:
                continue
            for i in claimants:               # every claimant submitted this amount, winner or not
                placed[i, j] = price[j] + increment
            winner = min(claimants, key=lambda s: order[s])
            price[j] = price[j] + increment
            holder[j] = winner
    alloc = Allocation(tuple(holder))
    payments = np.zeros(n)
    for j, h in enumerate(holder):
        if h is not None:
            payments[h] += price[j]
    truthful = vm.values.astype(float)
    return Benchmark(label="straightforward", citation_key="milgrom2000",
                     bids=placed, alloc=alloc, prices=price, payments=payments,
                     welfare=vm.welfare(alloc), revenue=float(payments.sum()),
                     note="the amounts a straightforward (demand-reduction-free) bidder actually SUBMITS: "
                          "standing + increment on each lot in its demanded bundle, up to the competitive "
                          "price; no priced action on lots outside its capacity- and synergy-constrained "
                          "demand",
                     detail={"rounds": rounds, "truthful_bids": truthful,
                             "demanded": [sorted(d) for d in demanded]})


# --------------------------------------------------------------------------------------------------------- #
# Multi-unit.
# --------------------------------------------------------------------------------------------------------- #
def marginal_value_schedule(vm: ValueModel, seat: int, n_units: int) -> np.ndarray:
    """A seat's TRUE marginal value for each successive identical unit: ``v_i * d_i^(r-1)`` for
    ``r = 1..min(k_i, n_units)``, zero beyond capacity. This is the demand-reduction-free schedule, and the
    reference the demand-reduction gradient is measured against [ausubel_cramton2014]."""
    base = float(vm.values[seat, 0])
    d = float(vm.decays[seat])
    k = min(int(vm.capacities[seat]), int(n_units))
    return np.array([base * d ** r for r in range(k)] + [0.0] * (n_units - k), dtype=float)


def uniform_price_benchmark(vm: ValueModel, *, n_units: int, tie_break, reserve: int = 0) -> Benchmark:
    """The demand-reduction-free uniform-price outcome: every seat submits its true marginal-value schedule.

    This is deliberately NOT the uniform-price equilibrium — under uniform pricing shading the inframarginal
    units is strictly optimal, so the true-value schedule is the COMPETITIVE reference against which that
    shading is measured [ausubel_cramton2014, pp. 1370-1378]. The note field says so, so the number is never
    read as an equilibrium prediction."""
    scheds = [marginal_value_schedule(vm, i, n_units) for i in range(vm.n_bidders)]
    units, price = uniform_price_clear([[int(round(x)) for x in s if x > 0] for s in scheds],
                                       supply=n_units, tie_break=tie_break, reserve=reserve)
    payments = units.astype(float) * price
    bids = np.array([[s[0] if len(s) else 0.0] for s in scheds])
    return Benchmark(label="demand_reduction_free", citation_key="ausubel_cramton2014", bids=bids,
                     alloc=Allocation((None,)), prices=np.array([float(price)]), payments=payments,
                     welfare=float(sum(vm.bundle_value(i, (0,) if units[i] else ()) for i in
                                       range(vm.n_bidders))),
                     revenue=float(payments.sum()),
                     note="true marginal-value schedules: the COMPETITIVE reference, not the uniform-price "
                          "equilibrium (which shades inframarginal units)",
                     detail={"units": units.tolist()})


def clinching_benchmark(vm: ValueModel, *, n_units: int, increment: int = 1, reserve: int = 0) -> Benchmark:
    """Truthful demand under the Ausubel clinching clock — an equilibrium of that mechanism, so unlike the
    uniform-price case this benchmark IS the equilibrium prediction [ausubel2004, pp. 1454-1460]."""
    scheds = [marginal_value_schedule(vm, i, n_units) for i in range(vm.n_bidders)]
    units, pay = clinching_prices([[int(round(x)) for x in s if x > 0] for s in scheds],
                                  supply=n_units, increment=increment, reserve=reserve)
    bids = np.array([[s[0] if len(s) else 0.0] for s in scheds])
    return Benchmark(label="truthful_demand", citation_key="ausubel2004", bids=bids,
                     alloc=Allocation((None,)), prices=np.array([float(pay.sum() / max(1, units.sum()))]),
                     payments=pay,
                     welfare=float(sum(vm.bundle_value(i, (0,) if units[i] else ())
                                       for i in range(vm.n_bidders))),
                     revenue=float(pay.sum()),
                     note="truthful demand, an equilibrium of the clinching rule",
                     detail={"units": units.tolist()})


# --------------------------------------------------------------------------------------------------------- #
# The one entry point.
# --------------------------------------------------------------------------------------------------------- #
def stage_benchmark(spec, t: int, *, posteriors=None) -> Benchmark:
    """The exact equilibrium benchmark for stage ``t`` of ``spec``, dispatching on the mechanism family.

    Parameters
    ----------
    spec : AuctionSpec
        The episode spec.
    t : int
        1-indexed stage.
    posteriors : list[RivalPosterior] | None
        Per-seat public posteriors, used only by the Dutch/first-price path under APV where the equilibrium
        is solved numerically. ``None`` builds them from the spec's public constants, which is what a seat
        holding only public information could do itself.
    """
    from .bidders import public_posteriors           # local import: bidders imports this module

    vm = ValueModel.from_spec(spec, t)
    st = spec.stage(t)
    mech = spec.mechanism
    if mech.family in ("sealed_single", "english"):
        if spec.value_structure == "interdep" and st.signals is not None:
            resale_grid = np.arange(40, 121, dtype=float)
            bids = np.array([[expected_value_given_winning(
                int(st.signals[i][0]),
                private_part=float(vm.values[i, 0]) - round(spec.gammas[i] * (st.resale or (0,))[0]),
                gamma=float(spec.gammas[i]), sigma_nu=float(spec.sigma_nu),
                n_rivals=spec.n_bidders - 1, resale_grid=resale_grid)] for i in range(spec.n_bidders)])
            return truthful_benchmark(vm, tie_break=st.tie_break, reserve=mech.reserve,
                                      pricing=mech.pricing, bids=bids[:, 0], budgets=st.budgets)
        return truthful_benchmark(vm, tie_break=st.tie_break, reserve=mech.reserve, pricing=mech.pricing,
                                  budgets=st.budgets)
    if mech.family == "dutch":
        if spec.value_structure == "ipv":
            bids = np.array([[rnne_symmetric_bid(vm.values[i, 0], spec.n_bidders)]
                             for i in range(spec.n_bidders)])
            label, key = "rnne_closed_form", "riley_samuelson1981"
        else:
            posts = posteriors if posteriors is not None else public_posteriors(spec, t)
            pmfs = [posts[i].value_pmf(0) for i in range(spec.n_bidders)]
            bids = np.array([[round(rnne_bid_against(float(vm.values[i, 0]),
                                                     [pmfs[k] for k in range(spec.n_bidders) if k != i],
                                                     lower=float(mech.reserve)))]
                             for i in range(spec.n_bidders)])
            label, key = "rnne_numeric", "riley_samuelson1981"
        winner, price = sealed_single_outcome([int(round(b[0])) for b in bids], pricing="first_price",
                                              tie_break=st.tie_break, reserve=mech.reserve)
        alloc = Allocation((winner,))
        payments = np.zeros(spec.n_bidders)
        if winner is not None:
            payments[winner] = price
        return Benchmark(label=label, citation_key=key, bids=bids, alloc=alloc,
                         prices=np.array([float(price) if winner is not None else 0.0]),
                         payments=payments, welfare=vm.welfare(alloc), revenue=float(payments.sum()),
                         note="risk-neutral first-price equilibrium; Dutch is strategically equivalent")
    if mech.family == "saa":
        # The benchmark is simulated under the CELL'S OWN round cap, not an uncapped clock. The cap is part of
        # the stage game that was actually played (5 rounds at 20 lots, design.md §3.3), and it binds hard: an
        # uncapped simulation walks prices to the competitive level while the played stage stops three or five
        # increments above the reserve, so scoring realized bids against uncapped benchmark bids booked the
        # ROUND CAP as suppression -- measured at s = 0.52 for the all_rational arm, which by construction
        # cannot collude.
        return saa_competitive_benchmark(vm, increment=mech.increment, reserve=mech.reserve,
                                         tie_break=st.tie_break, round_cap=mech.round_cap)
    if mech.family == "uniform_price":
        return uniform_price_benchmark(vm, n_units=mech.n_units, tie_break=st.tie_break,
                                       reserve=mech.reserve)
    if mech.family == "clinching":
        return clinching_benchmark(vm, n_units=mech.n_units, increment=mech.increment,
                                   reserve=mech.reserve)
    raise ValueError(f"no benchmark defined for mechanism family {mech.family!r}")
