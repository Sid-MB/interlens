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
# [rational_agents: viz] 2026-07-29

"""The plottable geometry of one negotiation instance: every deal placed in a 2-D scale-invariant embedding,
with the frontier, the axiomatic solution points, and each party's individually-best deal marked.

The problem this solves: with ``n`` parties a deal's utility vector lives in ``R^n``, so at ``n = 6`` there is no
honest "utility space" scatter to draw. The embedding here projects the exact ``|D| x n`` surplus table onto the
two axes that carry the normative content of a bargaining problem, both computed in
:func:`~interlens.arena.negotiation.solutions.normalized_surplus` coordinates (``clip(x_i, 0) / b_i``) so they
are exactly scale-invariant across arbitrary private score sheets:

- **x = joint welfare** — the mean normalized surplus over parties, ``mean_i x_i/b_i`` in ``[0, 1]``. The
  utilitarian axis: "how much total value did this deal create".
- **y = min surplus** — the minimum normalized surplus, ``min_i x_i/b_i`` in ``[0, 1]``. The egalitarian axis and
  exactly the quantity discrete Kalai-Smorodinsky maximizes: "how well off is the worst-treated party".

The projection is lossy by construction — two different deals can land on the same point — so a deal is never
*described* by its coordinates alone. Every mark carries its full per-party breakdown (:attr:`DealGeometry.u`,
``s``, ``xn``), which is what the visualizer's hover panel reads; the embedding only decides *where* it is drawn.
Both axes are monotone in the right direction (up and to the right is better for everybody), so the Pareto
frontier's image is the upper-right envelope of the cloud.

Everything is exact: the deal space is enumerated, so the frontier and every solution concept come from
``negotiation.solutions`` rather than from any sampling or hull approximation.

Example::

    geo = GameGeometry.from_instance(instance_dict)
    geo.n_deals, geo.n_parties                  # 243, 6
    geo.wx[geo.solution_index("nash")]          # the NBS's joint-welfare coordinate
    geo.party_best[0]                           # deal index of Avery's individually-best frontier deal
    geo.deal_index({"issue0": "opt1", ...})     # a named proposal -> its row in the utility matrix
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..negotiation.sheets import GameSpec
from ..negotiation.solutions import (all_solutions, ir_mask, nash_geomean, normalized_surplus, pareto_mask)
from .concepts import CONCEPT_LABELS

__all__ = ["CONCEPT_LABELS", "DealGeometry", "GameGeometry"]


@dataclass
class DealGeometry:
    """One deal's full record: where it plots, and how every party feels about it.

    ``index`` is the deal's row in the utility matrix (and its position in ``DealSpace.enumerate`` order);
    ``u``/``s``/``xn`` are the per-party utility, raw surplus, and normalized surplus vectors; ``wx``/``wy`` the
    embedding coordinates; ``pareto``/``ir``/``feasible`` its membership flags (Pareto-optimal, individually
    rational for every party, and passing this game's full agreement rule including veto/min-accept/structural
    constraints); ``d_frontier`` its normalized-surplus distance below the frontier (0 iff Pareto-optimal)."""

    index: int
    named: dict[str, str]
    u: list[float]
    s: list[float]
    xn: list[float]
    wx: float
    wy: float
    pareto: bool
    ir: bool
    feasible: bool
    d_frontier: float

    def to_json(self) -> dict:
        return {"index": self.index, "named": self.named, "u": self.u, "s": self.s, "xn": self.xn,
                "wx": self.wx, "wy": self.wy, "pareto": int(self.pareto), "ir": int(self.ir),
                "feasible": int(self.feasible), "d_frontier": self.d_frontier}


class GameGeometry:
    """The exact, fully-enumerated geometry of one negotiation instance, ready to plot.

    Built once per instance and shared by every episode played on it (both sides of a seat-swap comparison read
    the same object, so the two trajectories are guaranteed to be drawn against one identical frontier).

    Attributes
    ----------
    game : GameSpec
        The reconstructed game (deal space, private sheets, thresholds, protocol knobs).
    U, X, Xn : numpy.ndarray
        The ``|D| x n`` utility, raw-surplus, and normalized-surplus tables.
    wx, wy : numpy.ndarray
        The ``(|D|,)`` embedding coordinates (mean and min normalized surplus).
    pareto, ir, feasible : numpy.ndarray
        Boolean ``(|D|,)`` membership masks.
    solutions : dict
        ``{concept: SolutionPoint.to_json()}`` for every concept in
        :data:`~interlens.arena.viz.geometry.CONCEPT_LABELS` plus any extra the stored analysis carried.
    party_best : list[int]
        Per party, the deal index of its individually-best deal on the frontier — the "if this party could
        dictate the outcome (subject to everyone clearing their threshold and the deal being efficient)" point.
    """

    def __init__(self, game: GameSpec, solutions: dict | None = None, analysis: dict | None = None,
                 *, ceiling: float | None = None, floor: float | None = None):
        self.game = game
        self.analysis = analysis or {}
        self.ceiling, self.floor = ceiling, floor
        self.U = game.utility_matrix()
        self.tau = game.thresholds
        self.X = self.U - self.tau
        self.Xn = normalized_surplus(self.U, self.tau)
        self.wx = self.Xn.mean(axis=1)
        self.wy = self.Xn.min(axis=1)
        self.pareto = pareto_mask(self.U)
        self.ir = ir_mask(self.U, self.tau)
        self.feasible = game.feasible_mask(self.U)
        # Stored solutions are preferred over recomputing: they are what the run was actually scored against, so
        # a solver change after the fact shows up as a difference to investigate rather than being papered over.
        self.solutions = dict(solutions) if solutions else {
            name: point.to_json() for name, point in all_solutions(game.space, game.sheets).items()}
        self.solutions_source = "stored" if solutions else "recomputed"
        self._d_frontier = self._frontier_distances()
        self.party_best = self._party_best()

    # ------------------------------------------------------------------ construction --
    @staticmethod
    def from_instance(instance: dict) -> "GameGeometry | None":
        """The geometry of a stored ``Instance`` dict, or ``None`` if its payload is not a scorable game (so a
        caller can render a non-negotiation scenario's episode without the game panel instead of crashing)."""
        if not isinstance(instance, dict):
            return None
        payload = instance.get("payload")
        if not isinstance(payload, dict):
            return None
        spec = payload.get("game") or payload.get("spec") or payload
        try:
            game = GameSpec.from_json(spec)
        except Exception:
            return None
        solution = instance.get("solution") or {}
        return GameGeometry(game, solutions=solution.get("solutions"), analysis=solution,
                            ceiling=instance.get("ceiling"), floor=instance.get("floor"))

    def _frontier_distances(self) -> np.ndarray:
        """Every deal's Euclidean distance in normalized-surplus space to the nearest frontier deal (0 on the
        frontier). Computed as one ``|D| x |front|`` block rather than per-deal, so the whole cloud's
        below-frontier loss is available to the chart at no extra cost."""
        front = self.Xn[self.pareto]                                    # (|front|, n)
        diff = self.Xn[:, None, :] - front[None, :, :]                  # (|D|, |front|, n)
        return np.sqrt((diff * diff).sum(axis=2)).min(axis=1)

    def _party_best(self) -> list[int]:
        """Per party, its individually-best deal among the efficient deals that could actually close. Restricted
        to ``feasible & pareto`` (the deals the protocol permits AND that waste nothing); falls back to
        ``ir & pareto`` and then to ``pareto`` so a game with an empty feasible set still marks the points."""
        for mask in (self.feasible & self.pareto, self.ir & self.pareto, self.pareto):
            cand = np.nonzero(mask)[0]
            if cand.size:
                return [int(cand[int(np.argmax(self.X[cand, i]))]) for i in range(self.n_parties)]
        return [0] * self.n_parties

    # ------------------------------------------------------------------- accessors --
    @property
    def n_deals(self) -> int:
        """Deal-space size ``|D|``."""
        return int(self.U.shape[0])

    @property
    def n_parties(self) -> int:
        """Number of parties ``n``."""
        return int(self.U.shape[1])

    @property
    def parties(self) -> list[str]:
        """Score-sheet party ids in seat order (``"P0"``, ``"P1"``, ... — the seat *personas* live on the
        episode, not the game)."""
        return self.game.agents

    def solution_index(self, concept: str) -> int | None:
        """The deal index of a solution concept, or ``None`` if the instance carries no such concept."""
        point = self.solutions.get(concept)
        return None if point is None else int(point["index"])

    def deal_index(self, named: Any) -> int | None:
        """The deal index of a ``{issue_name: option_label}`` proposal (tolerant of case/whitespace, via
        ``DealSpace.parse``), or ``None`` if it is missing, malformed, or names an unknown option — which is
        exactly the case for a model's invalid proposal, so the caller gets ``None`` instead of an exception."""
        if isinstance(named, (list, tuple)):
            try:
                return int(self.game.space.index_of(tuple(int(o) for o in named)))
            except Exception:
                return None
        if not isinstance(named, dict):
            return None
        try:
            return int(self.game.space.index_of(self.game.space.parse(named)))
        except Exception:
            return None

    def at(self, index: int) -> DealGeometry:
        """The full :class:`DealGeometry` record for a deal index."""
        deal = self.game.space.deal_at(index)
        return DealGeometry(
            index=int(index), named=self.game.space.named(deal),
            u=[round(float(v), 4) for v in self.U[index]],
            s=[round(float(v), 4) for v in self.X[index]],
            xn=[round(float(v), 4) for v in self.Xn[index]],
            wx=round(float(self.wx[index]), 4), wy=round(float(self.wy[index]), 4),
            pareto=bool(self.pareto[index]), ir=bool(self.ir[index]), feasible=bool(self.feasible[index]),
            d_frontier=round(float(self._d_frontier[index]), 4))

    def welfare_of(self, index: int) -> dict:
        """The welfare scalars of one deal, in raw surplus units: ``usw`` (sum), ``esw`` (min), ``nsw_geomean``
        (the readable geometric-mean form of the Nash product), and the count of parties left below threshold."""
        s = self.X[index]
        return {"usw": round(float(s.sum()), 4), "esw": round(float(s.min()), 4),
                "nsw_geomean": round(nash_geomean([float(v) for v in s]), 4),
                "n_below_threshold": int((s < 0).sum())}

    def envelope(self) -> list[list[float]]:
        """The efficient envelope of the frontier IN THE 2-D EMBEDDING: the staircase of frontier deals that are
        non-dominated on ``(joint welfare, min surplus)`` themselves, ordered left to right.

        The projection is lossy, so a deal on the true ``R^n`` frontier can sit strictly inside this envelope —
        it is efficient overall while being beaten on both plotted summaries by some other efficient deal. The
        envelope is therefore drawn as the outer boundary of the achievable region and never used to decide
        whether a deal is Pareto-optimal; that always comes from :attr:`pareto`."""
        pts = sorted(((float(self.wx[i]), float(self.wy[i])) for i in np.nonzero(self.pareto)[0]),
                     key=lambda p: (-p[0], -p[1]))
        out: list[list[float]] = []
        best_y = -np.inf
        for x, y in pts:                     # sweeping right to left, keep each new record for min-surplus
            if y > best_y:
                out.append([round(x, 4), round(y, 4)])
                best_y = y
        return out[::-1]

    # ------------------------------------------------------------------- payload --
    def to_json(self) -> dict:
        """The whole geometry as one JSON payload for the browser: the game description, the per-deal tables (all
        ``|D|`` deals, so every point in the cloud is hoverable without a round trip), and the reference marks."""
        space = self.game.space
        return {
            "issues": [{"name": i.name, "options": list(i.options)} for i in space.issues],
            "shape": list(space.shape),
            "strides": list(space.strides()),
            "n_parties": self.n_parties,
            "parties": self.parties,
            "thresholds": [float(t) for t in self.tau],
            "sheets": [{"agent": s.agent, "threshold": float(s.threshold),
                        "values": [[float(v) for v in row] for row in s.values]} for s in self.game.sheets],
            "protocol": {"rounds": self.game.rounds, "info": self.game.info, "chat": self.game.chat,
                         "proposer": self.game.proposer, "veto_seats": self.game.veto_seats,
                         "min_accept": self.game.min_accept, "discount": self.game.discount,
                         "breakdown_risk": self.game.breakdown_risk, "constraint": self.game.constraint},
            "meta": self.game.meta,
            "ceiling": self.ceiling, "floor": self.floor,
            "counts": {k: self.analysis.get(k) for k in
                       ("deal_space_size", "pareto_count", "ir_count", "ir_pareto_count", "ir_pareto_fraction",
                        "dominated_acceptable_fraction", "empty_ir", "sparsity", "pairwise_iou",
                        "max_feasible_joint_surplus")},
            "ideal_surplus": [float(v) for v in self.X[self.ir].max(axis=0)] if self.ir.any()
                             else [float(v) for v in self.X.max(axis=0)],
            "deals": {
                "n": self.n_deals,
                "wx": [round(float(v), 4) for v in self.wx],
                "wy": [round(float(v), 4) for v in self.wy],
                "u": [[round(float(v), 4) for v in row] for row in self.U],
                "s": [[round(float(v), 4) for v in row] for row in self.X],
                "xn": [[round(float(v), 4) for v in row] for row in self.Xn],
                "pareto": [int(v) for v in self.pareto],
                "ir": [int(v) for v in self.ir],
                "feasible": [int(v) for v in self.feasible],
                "d_frontier": [round(float(v), 4) for v in self._d_frontier],
            },
            "envelope": self.envelope(),
            "solutions": {name: dict(point, label=CONCEPT_LABELS.get(name, name))
                          for name, point in self.solutions.items()},
            "solutions_source": self.solutions_source,
            "party_best": [{"party": i, "agent": self.parties[i], "index": int(idx),
                            "surplus": round(float(self.X[idx, i]), 4)}
                           for i, idx in enumerate(self.party_best)],
        }
