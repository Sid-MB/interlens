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
# [rational_agents scaffold: game-theory] 2026-07-23

"""Exact axiomatic solution concepts over the fully-enumerated deal space.

Everything here operates on the ``|D| x n`` utility matrix ``U`` (``sheets.utility_matrix``) and the reservation
vector ``tau``; the analysis object is the surplus ``X = U - tau``. Because the space is enumerated, every
concept is computed exactly (no sampling, no convex-hull approximation). Each function's docstring carries the
primary citation by key -- full text in ``references.py``.

Two solution concepts are **exactly scale-invariant** and therefore the only ones defensible across arbitrary
private score-sheet scales: the Nash Bargaining Solution (argmax of the surplus product) and Kalai-Smorodinsky
(argmax of the min normalized surplus). Utilitarian and egalitarian are **not** scale-invariant -- they are only
meaningful on a shared or normalized scale, and their docstrings flag this. Maximum Nash Welfare provides the
two-stage fallback when no deal clears every party's threshold (empty strict-IR set), where "no deal" is itself
the rational outcome.

Key terms: **IR set** = individually rational deals (all surpluses >= 0; strict > 0 for product solutions);
**ideal point** ``b_i`` = the best surplus party ``i`` can get among IR deals; **Pareto frontier** = deals not
utility-dominated by any other deal.

Low-level ``*_index`` functions return ``(best_index, tie_indices, note)`` on ``(U, tau)`` arrays; the
high-level :func:`all_solutions` / :func:`analyze` wrap them into :class:`SolutionPoint` objects and the
per-instance descriptor dict.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from typing import TYPE_CHECKING

import numpy as np

from .sheets import ScoreSheet, pairwise_iou, sparsity, utility_matrix
from .space import Deal, DealSpace

if TYPE_CHECKING:
    from collections.abc import Sequence

_TOL = 1e-9


# --- welfare & inequality scalars -------------------------------------------------------------------------
# Given ONE realized surplus vector ``x = (u_i(deal) - tau_i)``, how good is it? These are the scalar
# EVALUATORS, the counterpart to the argmax SOLVERS below (which pick the deal maximizing each): a scenario
# scores an episode's outcome with them, and the analysis layer aggregates them into a run's atlas. One home, so
# a run's reported welfare and the frontier it is compared against can never drift apart.
#
# Surplus units throughout, so parties on private point scales stay commensurable. Written in plain Python
# rather than numpy: these are called on n-element vectors (n ~ 2-6), and the exact summation order is part of
# the recorded numbers.

def welfare(x: "Sequence[float]") -> float:
    """Utilitarian social welfare ``USW = sum x_i``. NOT scale-invariant across parties — meaningful on
    normalized surpluses, and reported alongside ESW/NSW rather than alone [reproB_tmlr]."""
    return float(sum(x))


def egalitarian_welfare(x: "Sequence[float]") -> float:
    """Egalitarian (Rawlsian) welfare ``ESW = min x_i`` — "is any single party's interest being ignored". The
    quantity discrete-KS maximizes, up to per-party normalization. ``0.0`` for an empty vector."""
    return float(min(x)) if len(x) else 0.0


def nash_welfare(x: "Sequence[float]") -> float:
    """Nash social welfare ``NSW = prod x_i`` when every surplus is strictly positive, else ``0.0``.

    The Nash objective is ``argmax prod x_i`` over strictly-IR deals, so a party at or below its threshold is by
    convention outside the Nash set and contributes zero rather than a negative or spurious product — matching
    the discrete-NBS convention in :func:`max_nash_welfare_index`."""
    if len(x) == 0:
        return 0.0
    prod = 1.0
    for xi in x:
        if xi <= 0:
            return 0.0
        prod *= float(xi)
    return prod


def nash_geomean(x: "Sequence[float]") -> float:
    """Geometric mean of surpluses ``NSW^(1/n)``, in surplus units (``0.0`` if any party is non-positive, per the
    Nash convention above). The readable display form: raw ``prod x_i`` explodes with ``n`` (a 6-party game runs
    to 1e10) while the geometric mean stays on the same scale as USW/ESW, so cells compare at a glance."""
    n = len(x)
    if n == 0 or any(xi <= 0 for xi in x):
        return 0.0
    return math.exp(sum(math.log(float(xi)) for xi in x) / n)


def gini(x: "Sequence[float]", *, shift_negative: bool = False) -> float:
    """Gini coefficient of the surplus distribution (0 = perfectly equal, →1 = maximally unequal).

    Mean-absolute-difference form ``G = sum_ij |x_i - x_j| / (2 n sum_k x_k)``, which is the standard Gini and is
    algebraically identical to the sorted-rank form on non-negative data.

    Gini is only defined for a non-negative distribution with positive total, and a surplus vector can be
    negative when a party accepted below its threshold (an IR violation). ``shift_negative`` selects the policy
    for that case, because the two callers want different things and the choice changes the number:

    - ``False`` (default) — report ``nan`` when the total is non-positive, and take negatives at face value.
      "Undefined" is surfaced as undefined rather than silently reported as perfect equality. This is the
      analysis-layer policy.
    - ``True`` — translate the vector so its minimum is at 0 first, and return ``0.0`` for a non-positive total.
      Always yields a number, at the cost of measuring the *shifted* distribution's inequality. This is the
      per-episode outcome policy.

    The two agree exactly whenever every surplus is non-negative."""
    n = len(x)
    if n == 0:
        return 0.0 if shift_negative else float("nan")
    xs = [float(v) for v in x]
    if shift_negative:
        xs = [v - min(min(xs), 0.0) for v in xs]
    total = sum(xs)
    if total <= 0:
        return 0.0 if shift_negative else float("nan")
    mad = sum(abs(a - b) for a in xs for b in xs)
    return mad / (2.0 * n * total)


# --- masks and reference points --------------------------------------------------------------------------

def pareto_mask(U: np.ndarray) -> np.ndarray:
    """Boolean ``(|D|,)`` mask of Pareto-optimal deals: deal ``d`` is on the frontier iff no other deal weakly
    dominates it on every party and strictly on at least one. Brute force ``O(|D|^2 * n)`` -- milliseconds at
    |D|<=3125 [kung1975]. Deals with identical utility vectors do not dominate each other, so exact duplicates
    both stay on the frontier."""
    n_deals = U.shape[0]
    dominated = np.zeros(n_deals, dtype=bool)
    for k in range(n_deals):
        ge_all = np.all(U >= U[k], axis=1)      # deals weakly >= k on every party
        gt_any = np.any(U > U[k], axis=1)        # ... and strictly > on some party
        if np.any(ge_all & gt_any):
            dominated[k] = True
    return ~dominated


def ir_mask(U: np.ndarray, tau: np.ndarray, strict: bool = False) -> np.ndarray:
    """Boolean ``(|D|,)`` mask of individually rational (acceptable) deals: every party's surplus is ``>= 0``
    (``strict=True`` requires ``> 0``, the domain of the product solutions). An empty mask means "no deal" is the
    rational outcome (Nash 1950 p.158 -- the disagreement point) [nash1950]."""
    X = U - tau
    return np.all(X > 0, axis=1) if strict else np.all(X >= 0, axis=1)


def ideal_surplus(U: np.ndarray, tau: np.ndarray, restrict_ir: bool = True) -> np.ndarray:
    """The ideal-point surplus vector ``b`` of shape ``(n,)``: ``b_i`` = the largest surplus party ``i`` attains,
    over the IR set (``restrict_ir=True``) or over all deals. This is the normalizer for KS. If the IR set is
    empty, falls back to the max over all deals."""
    X = U - tau
    if restrict_ir:
        ir = np.all(X >= 0, axis=1)
        if ir.any():
            return X[ir].max(axis=0)
    return X.max(axis=0)


# --- tie-aware argmax helpers ----------------------------------------------------------------------------

def _argmax_ties(scores: np.ndarray, indices: np.ndarray) -> tuple[int, tuple[int, ...]]:
    """Argmax of ``scores`` (aligned to ``indices``) with a relative tolerance; returns the smallest tying index
    and the full tie set (all deterministic)."""
    m = float(scores.max())
    tol = _TOL * (1.0 + abs(m))
    keep = indices[scores >= m - tol]
    return int(keep.min()), tuple(int(x) for x in keep)


def _leximin_pick(mat: np.ndarray, indices: np.ndarray) -> tuple[int, tuple[int, ...]]:
    """Leximin-optimal row among ``indices``: maximize the ascending-sorted value vector lexicographically (raise
    the worst-off party first, then the next, ...). Returns the smallest tying index and the tie set. Values are
    rounded to 1e-9 before comparison so integer-derived scores tie cleanly."""
    best_key: tuple | None = None
    best_i = -1
    ties: list[int] = []
    for i in indices:
        i = int(i)
        key = tuple(round(x, 9) for x in sorted(mat[i].tolist()))
        if best_key is None or key > best_key:
            best_key, best_i, ties = key, i, [i]
        elif key == best_key:
            ties.append(i)
    return best_i, tuple(sorted(ties))


# --- solution concepts (each returns (best_index, tie_indices, note)) ------------------------------------

def nash_bargaining_index(U: np.ndarray, tau: np.ndarray) -> tuple[int, tuple[int, ...], str]:
    """Discrete **Nash Bargaining Solution**: ``argmax_{d: x_i(d) > 0 for all i} prod_i x_i(d)``, computed as
    ``argmax sum_i log x_i(d)`` for overflow safety [nash1950] (solution statement p.159; the non-convex/finite
    axiomatization is [mariotti1998]; the symmetric n-player product is [harsanyi1963]). **Exactly scale
    invariant** -- ``u_i -> a_i u_i + c_i`` (with ``tau_i`` moved likewise) multiplies the product by ``prod a_i``
    and leaves the argmax unchanged. If the strict-IR set is empty, falls back to Maximum Nash Welfare
    (:func:`max_nash_welfare_index`)."""
    X = U - tau
    strict = np.all(X > 0, axis=1)
    if not strict.any():
        idx, ties, _ = max_nash_welfare_index(U, tau)
        return idx, ties, "empty strict-IR set: fell back to Maximum Nash Welfare"
    idxs = np.nonzero(strict)[0]
    logprod = np.log(X[idxs]).sum(axis=1)
    best, ties = _argmax_ties(logprod, idxs)
    return best, ties, ""


def kalai_smorodinsky_index(U: np.ndarray, tau: np.ndarray) -> tuple[int, tuple[int, ...], str]:
    """Discrete **Kalai-Smorodinsky solution**: the Pareto-optimal IR deal maximizing the minimum normalized
    surplus ``min_i x_i(d)/b_i`` (``b`` = ideal point over IR), refined by leximin over the normalized surplus
    vector [ks1975]. **Exactly scale invariant** (``a_i`` cancels in ``x_i/b_i``). Original is 2-player: for
    ``n>2`` KS can miss Pareto optimality and no solution keeps all its axioms, so we take the Pareto-restricted
    max-min-normalized point with leximin ties [roth1979]; non-convex/finite cover [conley_wilkie1991]. Empty IR
    set falls back to Maximum Nash Welfare."""
    X = U - tau
    ir = np.all(X >= 0, axis=1)
    if not ir.any():
        idx, ties, _ = max_nash_welfare_index(U, tau)
        return idx, ties, "empty IR set: fell back to Maximum Nash Welfare"
    b = X[ir].max(axis=0)
    safe_b = np.where(b > 0, b, 1.0)
    norm = X / safe_b                       # normalized surplus for every deal (IR deals have X >= 0)
    cand = np.nonzero(ir & pareto_mask(U))[0]
    best, ties = _leximin_pick(norm, cand)
    return best, ties, ""


def egalitarian_index(U: np.ndarray, tau: np.ndarray) -> tuple[int, tuple[int, ...], str]:
    """Discrete **egalitarian (Kalai proportional) solution**: the IR deal maximizing ``min_i x_i(d)``, leximin
    refined [kalai1977]. **NOT scale invariant** -- it presupposes interpersonal utility comparability (in the
    title of the paper), so on arbitrary private scales the raw egalitarian point is meaningless across parties;
    on normalized surpluses ``x_i/b_i`` it collapses into KS. Only interpret it when the sheets share a scale by
    design (e.g. a common 0-100 budget)."""
    X = U - tau
    ir = np.nonzero(np.all(X >= 0, axis=1))[0]
    if ir.size == 0:
        idx, ties, _ = max_nash_welfare_index(U, tau)
        return idx, ties, "empty IR set: fell back to Maximum Nash Welfare"
    best, ties = _leximin_pick(X, ir)
    return best, ties, ""


def utilitarian_index(U: np.ndarray, tau: np.ndarray) -> tuple[int, tuple[int, ...], str]:
    """Discrete **utilitarian solution**: the IR deal maximizing the surplus sum ``sum_i x_i(d)`` [harsanyi1955].
    **NOT scale invariant** -- rescaling one party's sheet reweights the sum, so it is only meaningful on a shared
    or normalized scale (ANAC/GENIUS normalize to [0,1] first). The IR filter matters (a below-threshold party
    makes the sum meaningless); the ``tau``-shift alone does not move the argmax."""
    X = U - tau
    ir = np.nonzero(np.all(X >= 0, axis=1))[0]
    if ir.size == 0:
        idx, ties, _ = max_nash_welfare_index(U, tau)
        return idx, ties, "empty IR set: fell back to Maximum Nash Welfare"
    sums = X[ir].sum(axis=1)
    best, ties = _argmax_ties(sums, ir)
    return best, ties, ""


def max_nash_welfare_index(U: np.ndarray, tau: np.ndarray) -> tuple[int, tuple[int, ...], str]:
    """**Maximum Nash Welfare** with the two-stage empty-product rule [caragiannis2019] (Def. 3.1 + Algorithm 1,
    pp.12:7-12:8): first find the largest number of parties that can be made simultaneously positive-surplus by a
    single deal, then, among deals achieving that count, maximize the product of the positive surpluses (via
    ``sum log`` over the satisfied parties). When some deal clears every party's threshold this coincides exactly
    with the Nash Bargaining Solution; otherwise it is the least-bad diagnostic point for an empty strict-IR
    game. Scale-free [caragiannis2019] p.12:2."""
    X = U - tau
    pos = X > 0
    count = pos.sum(axis=1)
    maxc = int(count.max())
    cand = np.nonzero(count == maxc)[0]
    n = U.shape[1]
    if maxc == 0:
        # No deal makes anyone strictly better off than their BATNA: "no deal" is the rational outcome.
        return int(cand.min()), (int(cand.min()),), "no deal clears any party's threshold (no-deal is rational)"
    scores = np.array([np.log(X[k][pos[k]]).sum() for k in cand])
    best, ties = _argmax_ties(scores, cand)
    note = "" if maxc == n else f"empty strict-IR set: MNW over largest satisfiable coalition |S|={maxc}/{n}"
    return best, ties, note


# --- distance-to-frontier / distance-to-solution metrics -------------------------------------------------

def _normalized_surplus(U: np.ndarray, tau: np.ndarray) -> np.ndarray:
    """Per-deal nonnegative normalized surplus ``clip(x_i, 0) / b_i`` (``b_i`` = ideal over all deals), the
    scale-invariant coordinate the distance metrics live in. Below-threshold "gains" are clipped to 0 so they do
    not count as progress."""
    X = U - tau
    b = X.max(axis=0)
    safe_b = np.where(b > 0, b, 1.0)
    return np.clip(X, 0.0, None) / safe_b


def distance_to_frontier(U: np.ndarray, tau: np.ndarray, index: int) -> float:
    """Euclidean distance, in normalized-surplus space, from deal ``index`` to the nearest Pareto-frontier deal
    (0 iff ``index`` is itself Pareto-optimal). Scale-invariant. This is the centipawn-loss-style denominator for
    per-turn divergence: how far a chosen deal sits below the efficient frontier."""
    Xn = _normalized_surplus(U, tau)
    front = np.nonzero(pareto_mask(U))[0]
    diffs = Xn[front] - Xn[index]
    return float(np.sqrt((diffs * diffs).sum(axis=1)).min())


def distance_to_solution(U: np.ndarray, tau: np.ndarray, index: int, target_index: int) -> float:
    """Euclidean distance, in normalized-surplus space, between deal ``index`` and a reference solution deal
    ``target_index`` (e.g. the NBS or KS index). Scale-invariant; 0 iff the two deals give identical normalized
    surplus."""
    Xn = _normalized_surplus(U, tau)
    diff = Xn[index] - Xn[target_index]
    return float(np.sqrt((diff * diff).sum()))


# --- high-level solution points + per-instance analysis --------------------------------------------------

@dataclass
class SolutionPoint:
    """One solution concept's chosen deal, resolved against a concrete game.

    ``index`` is the deal's flat position (row in ``U``), ``deal`` the option-index tuple, ``named`` its
    human-readable form; ``utilities`` and ``surpluses`` are the per-party vectors at that deal; ``ties`` lists
    every equally-optimal deal (>=1); ``note`` records fallbacks/caveats; ``scale_invariant`` flags whether the
    concept is defensible across arbitrary private scales."""

    concept: str
    index: int
    deal: Deal
    named: dict[str, str]
    utilities: tuple[float, ...]
    surpluses: tuple[float, ...]
    ties: tuple[int, ...]
    note: str = ""
    scale_invariant: bool = True

    def to_json(self) -> dict:
        """JSON-ready dict."""
        return {
            "concept": self.concept, "index": self.index, "deal": list(self.deal), "named": self.named,
            "utilities": list(self.utilities), "surpluses": list(self.surpluses), "ties": list(self.ties),
            "note": self.note, "scale_invariant": self.scale_invariant,
        }


# name -> (index function, is-scale-invariant)
_CONCEPTS = {
    "nash": (nash_bargaining_index, True),
    "kalai_smorodinsky": (kalai_smorodinsky_index, True),
    "egalitarian": (egalitarian_index, False),
    "utilitarian": (utilitarian_index, False),
    "max_nash_welfare": (max_nash_welfare_index, True),
}


def _point(space: DealSpace, U: np.ndarray, tau: np.ndarray, concept: str) -> SolutionPoint:
    fn, inv = _CONCEPTS[concept]
    idx, ties, note = fn(U, tau)
    deal = space.deal_at(idx)
    return SolutionPoint(
        concept=concept, index=idx, deal=deal, named=space.named(deal),
        utilities=tuple(float(x) for x in U[idx]), surpluses=tuple(float(x) for x in (U[idx] - tau)),
        ties=ties, note=note, scale_invariant=inv,
    )


def all_solutions(space: DealSpace, sheets: tuple[ScoreSheet, ...] | list[ScoreSheet]) -> dict[str, SolutionPoint]:
    """Compute every solution concept for a game, returning ``{concept_name: SolutionPoint}``. Builds the utility
    matrix once and reuses it."""
    U = utility_matrix(space, sheets)
    tau = np.array([s.threshold for s in sheets], dtype=float)
    return {name: _point(space, U, tau, name) for name in _CONCEPTS}


def analyze(space: DealSpace, sheets: tuple[ScoreSheet, ...] | list[ScoreSheet],
            acceptable_mask: np.ndarray | None = None) -> dict:
    """The precomputed per-instance analysis dict every generated game ships with.

    Contains: ``deal_space_size`` |D|, ``n_parties``, ``pareto_count``, ``ir_count`` |IR|, ``ir_pareto_count``
    |IR∩Pareto|, ``ir_pareto_fraction`` |IR∩Pareto|/|IR| (how near-zero-sum the acceptable set is),
    ``dominated_acceptable_fraction`` = 1 - that (the central score-sheet-repair target [reproA2025]),
    ``empty_ir``, ``ideal_surplus`` (over IR), the score-sheet descriptors ``sparsity`` and ``pairwise_iou``
    [reproB_tmlr], and every solution point under ``solutions``. Pass ``acceptable_mask`` to score the fraction
    against a custom agreement rule (e.g. ``GameSpec.feasible_mask``); default is unanimity IR (all surplus >=
    0). Fully JSON-serializable."""
    U = utility_matrix(space, sheets)
    tau = np.array([s.threshold for s in sheets], dtype=float)
    X = U - tau
    pareto = pareto_mask(U)
    acc = ir_mask(U, tau) if acceptable_mask is None else acceptable_mask
    ir_count = int(acc.sum())
    ir_pareto = int((acc & pareto).sum())
    frac_front = (ir_pareto / ir_count) if ir_count else 0.0
    # Best joint over the acceptable set: the utilitarian-over-feasible point (a natural primary-score ceiling
    # for a scenario whose score is normalized joint value on the agreed deal).
    if ir_count:
        acc_idx = np.nonzero(acc)[0]
        best = int(acc_idx[int(np.argmax(X[acc_idx].sum(axis=1)))])
        max_joint_surplus, max_joint_utility = float(X[best].sum()), float(U[best].sum())
        best_deal = list(space.deal_at(best))
    else:
        max_joint_surplus, max_joint_utility, best_deal = 0.0, 0.0, None
    return {
        "deal_space_size": int(space.size),
        "n_parties": len(sheets),
        "pareto_count": int(pareto.sum()),
        "ir_count": ir_count,
        "ir_pareto_count": ir_pareto,
        "ir_pareto_fraction": frac_front,
        "dominated_acceptable_fraction": (1.0 - frac_front) if ir_count else 0.0,
        "empty_ir": ir_count == 0,
        "ideal_surplus": [float(x) for x in ideal_surplus(U, tau)],
        "max_feasible_joint_surplus": max_joint_surplus,
        "max_feasible_joint_utility": max_joint_utility,
        "max_feasible_joint_deal": best_deal,
        "sparsity": sparsity(sheets),
        "pairwise_iou": pairwise_iou(sheets),
        "solutions": {name: _point(space, U, tau, name).to_json() for name in _CONCEPTS},
    }
