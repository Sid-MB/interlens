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

"""Scorable-negotiation scenario generator with the score-sheet repairs the reproducibility studies demand.

The generator draws private additive score sheets from an explicit issue-type mix, calibrates thresholds to a
target acceptable-set size, and -- the central repair -- rejection-samples over seeds to hit a target fraction of
acceptable deals that are Pareto-*dominated*. The prior benchmark had 80.5% of acceptable deals ON the frontier,
making the game near-zero-sum the moment it was feasible [reproA2025]; leaving dominated-but-acceptable deals in
play (target ~50-70% dominated) restores genuine room to negotiate. Every knob is documented; every generated
game ships with a precomputed analysis dict (:func:`interlens.arena.negotiation.solutions.analyze`) whose
descriptors are *verified by enumeration*, so a caller can always re-check what it got.

Issue types (LAMEN / DESIGN.md §2.3), which shape the cross-party correlation of the value columns:

- ``distributive`` -- opposed preferences (a fixed pie): parties split into camps with reversed option
  rankings and high weight, so acceptable deals get pushed onto the frontier (near-zero-sum).
- ``compatible``   -- a shared option ranking: everyone prefers the same option, so the worse options are
  Pareto-dominated-for-all yet may stay acceptable under loose thresholds (a prime source of dominated slack).
- ``integrative``  -- parties weight *different* issues (non-carers score the issue 0, creating sparsity), so
  conceding an issue you don't care about to someone who does is a free logroll; failing to do so lands you at a
  dominated interior deal.

The mix is thus the geometric lever on the dominated fraction (threshold calibration fixes the *size*
independently), and seed rejection-sampling fine-tunes it. Semantic decorrelation (``decorrelate=True``) permutes
each issue's option order and uses neutral labels so no public role text can leak preferences (Study A's
communication-free baseline otherwise matched the full game) [reproA2025].

Example::

    game, analysis = generate_game(n_parties=5, n_issues=5, n_options=4,
                                   feasible_fraction=0.12, dominated_target=0.6, seed=1)
    analysis["dominated_acceptable_fraction"]   # ~0.6, verified by enumeration
    analysis["ir_count"], game.n_parties
"""
from __future__ import annotations

import argparse
import json
from enum import Enum
from pathlib import Path
from typing import Sequence

import numpy as np

from ..schema import Instance, new_id
from .sheets import GameSpec, ScoreSheet, utility_matrix
from .solutions import analyze, ir_mask
from .space import DealSpace, Issue

SCALE = 100.0   # per (issue, party) value magnitude ceiling; utilities land on private, un-shared scales

# Default difficulty ladder for the arena-Instance bridge: level -> generator-knob overrides. Higher level =
# harder = smaller feasible set (feasible_fraction shrinks; dominated slack held at the repaired ~0.6). Mirrors
# the base ladder's shrinking feasible-set buckets. Override per level via ``generate_instance(..., ladder=...)``.
INSTANCE_LADDER: list[dict] = [
    {"feasible_fraction": 0.16, "dominated_target": 0.6},   # L0 (easiest)
    {"feasible_fraction": 0.10, "dominated_target": 0.6},
    {"feasible_fraction": 0.06, "dominated_target": 0.6},
    {"feasible_fraction": 0.03, "dominated_target": 0.6},
    {"feasible_fraction": 0.015, "dominated_target": 0.6},  # L4 (hardest)
]

# Per-round discount delta the generated instance bank ships with. Deliberately < 1: with only a hard turn
# deadline and delta = 1 the rational baseline is brinkmanship (both wait to the deadline), so interior
# concession -- the behavior the LLM-vs-rational-agent comparison is about -- is only rational under delta < 1
# [sandholm_vulkan1999]. 0.95 matches the value the impatience-sensitive oracles were tuned against. Override
# per instance with ``generate_instance(level, seed, discount=1.0)`` for a brinkmanship-baseline ablation arm.
LADDER_DISCOUNT = 0.95


class IssueType(str, Enum):
    """The three issue archetypes that set how parties' value columns correlate (see module docstring)."""

    DISTRIBUTIVE = "distributive"
    INTEGRATIVE = "integrative"
    COMPATIBLE = "compatible"


def _assign_types(n_issues: int, mix: tuple[float, float, float], rng: np.random.Generator) -> list[IssueType]:
    """Turn a ``(distributive, integrative, compatible)`` fraction triple into a per-issue type list of length
    ``n_issues`` (largest-remainder rounding), shuffled by ``rng``."""
    order = [IssueType.DISTRIBUTIVE, IssueType.INTEGRATIVE, IssueType.COMPATIBLE]
    w = np.array(mix, dtype=float)
    w = w / w.sum() if w.sum() > 0 else np.ones(3) / 3
    raw = w * n_issues
    counts = np.floor(raw).astype(int)
    for i in np.argsort(-(raw - counts))[: n_issues - counts.sum()]:
        counts[i] += 1
    types = [t for t, c in zip(order, counts) for _ in range(int(c))]
    rng.shuffle(types)
    return types


def _quality(k: int, rng: np.random.Generator) -> np.ndarray:
    """A random strict option-quality vector over ``k`` options: ``linspace(0,1,k)`` under a random permutation."""
    base = np.linspace(0.0, 1.0, k)
    return base[rng.permutation(k)]


def _issue_column(itype: IssueType, k: int, n: int, rng: np.random.Generator) -> np.ndarray:
    """One issue's ``(k, n)`` value block (option x party), integer-valued, following its archetype."""
    col = np.zeros((k, n), dtype=float)
    if itype is IssueType.COMPATIBLE:
        q = _quality(k, rng)                                   # one shared ranking
        for i in range(n):
            col[:, i] = rng.uniform(20, 60) * q
    elif itype is IssueType.DISTRIBUTIVE:
        q = _quality(k, rng)
        camp = rng.permutation(n) < (n // 2 if n > 1 else 1)   # split parties into two opposed camps
        for i in range(n):
            qi = q if camp[i] else (1.0 - q)                   # reversed ranking for the other camp
            col[:, i] = rng.uniform(40, 100) * qi
    else:  # INTEGRATIVE: a subset of parties care (high weight), the rest score it 0 (sparsity + logrolling)
        n_care = max(1, n // 2)
        carers = rng.choice(n, size=n_care, replace=False)
        for i in carers:
            col[:, i] = rng.uniform(40, 100) * _quality(k, rng)
    return np.rint(col)


def _sheets_from_columns(columns: list[np.ndarray], names: list[str], tau: np.ndarray) -> tuple[ScoreSheet, ...]:
    """Assemble per-party :class:`ScoreSheet` objects from a list of ``(k_j, n)`` issue blocks and thresholds."""
    n = len(names)
    sheets = []
    for i in range(n):
        values = tuple(tuple(float(columns[j][o, i]) for o in range(columns[j].shape[0])) for j in range(len(columns)))
        sheets.append(ScoreSheet(names[i], values, float(tau[i])))
    return tuple(sheets)


def _calibrate_thresholds(U: np.ndarray, target_count: int, iters: int = 44) -> tuple[np.ndarray, int]:
    """Choose a common utility quantile ``q`` and set each party's threshold to its own ``q``-th utility
    percentile so the unanimity acceptable set is as close as possible to ``target_count`` deals. The acceptable
    count is monotone non-increasing in ``q`` (higher thresholds -> fewer deals clear all parties), so bisect
    ``q`` in ``[0, 1]`` and keep the best-hitting thresholds seen."""
    lo, hi = 0.0, 1.0
    best: tuple[np.ndarray, int] | None = None
    for _ in range(iters):
        q = 0.5 * (lo + hi)
        tau = np.quantile(U, q, axis=0)
        cnt = int(np.all(U >= tau, axis=1).sum())
        if best is None or abs(cnt - target_count) < abs(best[1] - target_count):
            best = (tau, cnt)
        if cnt > target_count:
            lo = q          # too many acceptable -> tighten (raise q)
        else:
            hi = q          # too few acceptable -> loosen (lower q)
    return best             # type: ignore[return-value]


def _decorrelate(columns: list[np.ndarray], rng: np.random.Generator) -> tuple[list[np.ndarray], list[list[int]]]:
    """Permute each issue's option rows by an independent random permutation and return the permuted columns plus
    the permutations (so option *index* order carries no cross-issue signal). Returns ``(columns, perms)``."""
    perms = []
    out = []
    for col in columns:
        p = rng.permutation(col.shape[0])
        out.append(col[p])
        perms.append([int(x) for x in p])
    return out, perms


def generate_game(
    n_parties: int = 6,
    n_issues: int = 5,
    n_options: int | Sequence[int] = 4,
    mix: tuple[float, float, float] = (0.4, 0.4, 0.2),
    issue_types: Sequence[str] | None = None,
    feasible_fraction: float = 0.10,
    feasible_tol: float = 0.6,
    dominated_target: float | None = 0.6,
    dominated_tol: float = 0.12,
    auto_mix: bool = True,
    decorrelate: bool = True,
    rounds: int = 4,
    info: str = "full",
    chat: bool = True,
    proposer: int = 0,
    veto: int | None = 1,
    discount: float = 1.0,
    breakdown_risk: float = 0.0,
    max_tries: int = 600,
    seed: int = 0,
) -> tuple[GameSpec, dict]:
    """Generate one scorable-negotiation game plus its enumeration-verified analysis dict.

    Parameters
    ----------
    n_parties : number of negotiating parties ``n``.
    n_issues : number of issues ``J``.
    n_options : options per issue -- one int (same for all issues) or a per-issue sequence of length ``n_issues``.
        Deal space size is ``prod`` of these; keep it enumerable (<= ~3125).
    mix : ``(distributive, integrative, compatible)`` fractions used to assign each issue a type (normalized
        internally). The geometric lever on the dominated-acceptable fraction: more compatible/integrative
        content -> more dominated-but-acceptable slack; more distributive content -> nearer zero-sum.
    issue_types : explicit per-issue type list (strings/``IssueType``); overrides ``mix`` when given.
    feasible_fraction : target size of the unanimity acceptable (IR) set as a fraction of ``|D|`` -- the
        difficulty dial (smaller = harder to find a deal). Thresholds are calibrated to hit it.
    feasible_tol : relative tolerance on the acceptable count; a candidate counts as size-OK when its count is
        within ``feasible_tol`` of the target (always at least +/-1 deal of slack).
    dominated_target : target fraction of acceptable deals that are Pareto-dominated (the central repair). Set
        ``None`` to skip the search and just return the first size-OK candidate.
    dominated_tol : accept-and-stop tolerance on the dominated fraction; otherwise the closest candidate over
        ``max_tries`` seeds is returned.
    auto_mix : when True and ``dominated_target`` is set and ``issue_types`` is not given, also sweep the
        distributive fraction of the issue mix (more distributive -> nearer zero-sum -> lower dominated fraction)
        so a low or high target is reachable that a single fixed mix could not hit by reseeding alone. ``mix`` is
        the sweep center; set ``auto_mix=False`` to hold ``mix`` fixed.
    decorrelate : when True, permute each issue's option order and use neutral option labels so no public role
        text can leak preferences (the mandatory control from Study A) [reproA2025].
    rounds, info, chat, proposer, veto : protocol knobs stored on the returned ``GameSpec`` (see
        :class:`~interlens.arena.negotiation.sheets.GameSpec`). Acceptable-set analysis uses unanimity IR.
    discount : per-round discount ``delta`` in (0, 1] stored on the game (default 1.0 = no impatience). With
        only a hard deadline and ``delta = 1``, the rational baseline is deadline brinkmanship, so a game meant
        to elicit interior concession should set ``delta < 1`` [sandholm_vulkan1999] (the instance ladder does).
        The equilibrium/acceptance oracles read this as their single source of truth.
    breakdown_risk : per-round exogenous-breakdown probability in [0, 1) stored on the game (default 0.0). An
        alternative to discounting for making interior concession rational.
    max_tries : rejection-sampling budget (distinct seeds tried) when ``dominated_target`` is set.
    seed : base RNG seed; try ``t`` uses ``seed*100003 + t`` so different base seeds give different games.

    Returns
    -------
    ``(GameSpec, analysis)`` where ``analysis`` is :func:`solutions.analyze`'s dict (all descriptors verified by
    enumeration). ``GameSpec.meta`` records the generator provenance and the achieved fractions, and
    ``analysis["generator"]`` mirrors the request/achievement so failures to hit a target are visible, never
    silent.
    """
    if isinstance(n_options, int):
        opts = [n_options] * n_issues
    else:
        opts = list(n_options)
        if len(opts) != n_issues:
            raise ValueError(f"n_options sequence has {len(opts)} entries, need n_issues={n_issues}")
    names = [f"P{i}" for i in range(n_parties)]
    target_count = max(0, round(feasible_fraction * int(np.prod(opts))))
    size_slack = max(1, round(feasible_tol * target_count))
    issues = tuple(Issue(f"issue{j}", tuple(f"opt{o}" for o in range(opts[j]))) for j in range(n_issues))
    space = DealSpace(issues)

    def _candidate(seed_val: int, types: list[IssueType]) -> tuple[float, GameSpec, dict, bool, float]:
        """One draw: sheets from the given issue types, thresholds calibrated to the size target, analysis
        computed. Returns ``(loss, game, analysis, size_ok, dom_pen)``."""
        rng = np.random.default_rng(seed_val)
        columns = [_issue_column(types[j], opts[j], n_parties, rng) for j in range(n_issues)]
        perms = None
        if decorrelate:
            columns, perms = _decorrelate(columns, rng)
        sheets0 = _sheets_from_columns(columns, names, np.zeros(n_parties))
        U = utility_matrix(space, sheets0)
        tau, cnt = _calibrate_thresholds(U, target_count)
        sheets = _sheets_from_columns(columns, names, tau)
        analysis = analyze(space, sheets, acceptable_mask=ir_mask(U, tau))
        dom = analysis["dominated_acceptable_fraction"]
        size_ok = abs(cnt - target_count) <= size_slack
        size_pen = 0.0 if size_ok else 10.0 * (abs(cnt - target_count) / max(1, target_count))
        dom_pen = 0.0 if dominated_target is None else abs(dom - dominated_target)
        game = GameSpec(space=space, sheets=sheets, rounds=rounds, info=info, chat=chat,
                        proposer=proposer, veto=veto, min_accept=None,
                        discount=discount, breakdown_risk=breakdown_risk,
                        meta={"generator": "rational_agents.generate_game", "seed": seed,
                              "issue_types": [ti.value for ti in types], "option_perms": perms,
                              "decorrelate": decorrelate,
                              "targets": {"feasible_fraction": feasible_fraction, "feasible_count": target_count,
                                          "dominated_target": dominated_target},
                              "achieved": {"ir_count": int(cnt), "dominated_acceptable_fraction": dom}})
        analysis["generator"] = game.meta
        return size_pen + dom_pen, game, analysis, size_ok, dom_pen

    # The mix grid: an explicit issue-type list pins the types; otherwise, when a dominated target is set and
    # auto_mix is on, sweep the distributive fraction (the geometric lever on dominated slack) around `mix`,
    # holding the integrative:compatible ratio; else just use `mix`.
    if issue_types is not None:
        fixed = [IssueType(s) for s in issue_types]
        mixes: list = [("fixed", fixed)]
    elif auto_mix and dominated_target is not None:
        ic = np.array(mix[1:], dtype=float)
        ic = ic / ic.sum() if ic.sum() > 0 else np.array([0.5, 0.5])
        ds = sorted({round(mix[0], 3), 0.2, 0.35, 0.5, 0.65, 0.8})
        mixes = [(f"d={d}", (d, float((1 - d) * ic[0]), float((1 - d) * ic[1]))) for d in ds]
    else:
        mixes = [("mix", mix)]

    per_mix = max(1, max_tries // len(mixes))
    best = None                      # (loss, GameSpec, analysis)
    for gi, (_, spec) in enumerate(mixes):
        for t in range(per_mix):
            sv = seed * 100003 + gi * 7919 + t
            types = spec if isinstance(spec, list) else _assign_types(n_issues, spec, np.random.default_rng(sv))
            loss, game, analysis, size_ok, dom_pen = _candidate(sv, types)
            if best is None or loss < best[0]:
                best = (loss, game, analysis)
            if size_ok and (dominated_target is None or dom_pen <= dominated_tol):
                return game, analysis

    return best[1], best[2]          # type: ignore[index]


def generate_games(count: int, seed: int = 0, **kwargs) -> list[tuple[GameSpec, dict]]:
    """Generate ``count`` independent games with consecutive base seeds ``seed, seed+1, ...`` (all other knobs
    forwarded to :func:`generate_game`)."""
    return [generate_game(seed=seed + i, **kwargs) for i in range(count)]


def build_instance(game: GameSpec, analysis: dict, *, name: str, level: int, seed: int,
                   id_prefix: str | None = None) -> Instance:
    """Wrap a generated ``(GameSpec, analysis)`` into a solver-verified arena :class:`~interlens.arena.schema.Instance`.

    Primary-score convention (matching the shipped ``negotiation`` scenario): the episode's primary score is the
    normalized joint value on the agreed deal, ``joint_utility(deal) / max_feasible_joint_utility`` (no deal =
    0). So the exact ``ceiling`` is ``1.0`` (the best feasible deal) and the reference ``floor`` is
    ``mean_feasible_joint / max_feasible_joint`` -- an average-feasible-deal policy. ``payload`` is
    ``GameSpec.to_json()`` (round-trips back via ``GameSpec.from_json``); ``solution`` is the full
    :func:`~interlens.arena.negotiation.solutions.analyze` dict (descriptors + every solution point), so scorers
    and analyses read it straight from the stored Instance without re-solving. If the feasible set is empty
    (no-deal is the rational outcome) ceiling/floor are both ``0.0``. ``name`` is the scenario name the calling
    scenario passes in, so ``Instance.scenario`` matches it."""
    U = game.utility_matrix()
    acc = game.feasible_mask(U)
    max_joint = float(analysis.get("max_feasible_joint_utility", 0.0))
    if acc.any() and max_joint > 0:
        ceiling = 1.0
        floor = round(float(U.sum(axis=1)[acc].mean()) / max_joint, 4)
    else:
        ceiling, floor = 0.0, 0.0
    prefix = id_prefix or f"{name}-L{level}"
    return Instance(new_id(prefix), name, level, seed, game.to_json(), ceiling, floor, analysis)


def generate_instance(level: int, seed: int, *, name: str = "scorable_negotiation",
                      ladder: list[dict] | None = None, **overrides) -> Instance:
    """Generate one solver-verified arena :class:`~interlens.arena.schema.Instance` at difficulty ``level`` from
    ``seed`` -- the bridge a ``ScorableNegotiation`` scenario's ``generate_instance`` delegates to.

    Maps ``level`` through ``ladder`` (default :data:`INSTANCE_LADDER`, shrinking feasible set with level) to
    :func:`generate_game` knobs, generates the game plus its enumeration-verified analysis, and wraps them via
    :func:`build_instance`. The bank ships with per-round discount :data:`LADDER_DISCOUNT` (< 1, so interior
    concession is rational rather than deadline brinkmanship [sandholm_vulkan1999]); pass ``discount=1.0`` (or any
    other knob) via ``**overrides`` to change it -- e.g. a brinkmanship-baseline ablation arm. Other overridable
    knobs: ``n_parties``, ``n_issues``, ``n_options``, ``mix``, ``max_tries``, ``breakdown_risk``. ``name`` sets
    ``Instance.scenario`` so a scenario passes ``self.name``. The payload is deterministic per ``(level, seed)``
    (the instance id is fresh each call, per the arena convention)."""
    ladder = ladder if ladder is not None else INSTANCE_LADDER
    if not 0 <= level < len(ladder):
        raise IndexError(f"level {level} out of range for a ladder of {len(ladder)} levels")
    knobs = {"discount": LADDER_DISCOUNT, **ladder[level], **overrides}
    game, analysis = generate_game(seed=seed, **knobs)
    return build_instance(game, analysis, name=name, level=level, seed=seed)


def _cli() -> None:
    """Command-line entry: generate games to a JSON file of ``{spec, analysis}`` records for offline inspection.
    Every argument mirrors a :func:`generate_game` knob."""
    p = argparse.ArgumentParser(
        description="Generate scorable-negotiation games (repaired score sheets) + verified analysis.")
    p.add_argument("--n-parties", type=int, default=6, help="number of negotiating parties n")
    p.add_argument("--n-issues", type=int, default=5, help="number of issues J")
    p.add_argument("--n-options", type=int, default=4, help="options per issue (same for all issues)")
    p.add_argument("--mix", type=float, nargs=3, default=(0.4, 0.4, 0.2),
                   metavar=("DISTRIB", "INTEG", "COMPAT"),
                   help="issue-type fractions (distributive integrative compatible); the lever on dominated slack")
    p.add_argument("--feasible-fraction", type=float, default=0.10,
                   help="target |acceptable|/|D| (difficulty dial; smaller = harder to find a deal)")
    p.add_argument("--dominated-target", type=float, default=0.6,
                   help="target fraction of acceptable deals that are Pareto-dominated (the score-sheet repair)")
    p.add_argument("--discount", type=float, default=1.0,
                   help="per-round discount delta in (0,1] stored on each game; <1 makes interior concession "
                        "rational rather than deadline brinkmanship (Sandholm-Vulkan). Default 1.0 (neutral)")
    p.add_argument("--no-decorrelate", action="store_true",
                   help="disable option-order decorrelation (keep the natural option ordering)")
    p.add_argument("--count", type=int, default=1, help="number of games to generate")
    p.add_argument("--seed", type=int, default=0, help="base RNG seed (game i uses seed+i)")
    p.add_argument("--max-tries", type=int, default=600, help="rejection-sampling budget per game")
    p.add_argument("--out", type=str, required=True, help="output JSON path")
    a = p.parse_args()

    games = generate_games(a.count, seed=a.seed, n_parties=a.n_parties, n_issues=a.n_issues,
                           n_options=a.n_options, mix=tuple(a.mix), feasible_fraction=a.feasible_fraction,
                           dominated_target=a.dominated_target, decorrelate=not a.no_decorrelate,
                           discount=a.discount, max_tries=a.max_tries)
    records = [{"spec": g.to_json(), "analysis": an} for g, an in games]
    Path(a.out).write_text(json.dumps(records, ensure_ascii=False, indent=1))
    print(f"wrote {len(records)} game(s) to {a.out}")
    for i, (_, an) in enumerate(games):
        gen = an["generator"]["achieved"]
        print(f"  game {i}: |D|={an['deal_space_size']} |IR|={gen['ir_count']} "
              f"dominated={gen['dominated_acceptable_fraction']:.2f} "
              f"sparsity={an['sparsity']:.2f} IoU={an['pairwise_iou']:.2f}")


if __name__ == "__main__":
    _cli()
