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
"""``GameAnalysis``: the solved-game bundle the metrics read — the adapter seam between interlens'
``GameSpec``/``solutions.py`` and the pure metric math. Holds everything the metrics need about the *game* (not
any one episode): thresholds, score sheets (to score any deal into a surplus vector), the Pareto frontier, and
the named solution points (NBS/KS/MNW/utilitarian/egalitarian) as surplus vectors, plus §2.1 descriptors.

Constructed either from a stored ``Instance`` (``from_instance`` — reads interlens' precomputed analysis, no
re-solving) or from raw sheets (``from_sheets`` — self-contained fallback for fixtures; enumerates the frontier
and welfare argmaxes, leaves the axiomatic NBS/KS/MNW ``None`` unless supplied). ``Deal`` is
``tuple[int, ...]`` (one option index per issue); ``canonical_deal`` maps the forms a stored action may carry
(index tuple/list, or ``{issue_name: option}`` dict) onto it.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Sequence

from . import surplus as S

Deal = tuple[int, ...]

# the named solution points a GameAnalysis may carry, as surplus vectors (None when not computed/available)
POINT_NAMES = ("nbs", "ks", "mnw", "utilitarian", "egalitarian")


@dataclass
class GameAnalysis:
	"""Solved-game bundle: surplus geometry + solution points + descriptors for one instance."""

	n_agents: int
	thresholds: tuple[float, ...]                       # tau_i per party
	issues: list[tuple[str, list[str]]] = field(default_factory=list)   # (name, option-names) per issue
	sheets: list[list[list[float]]] | None = None       # sheets[agent][issue][option] = raw points
	frontier: list[tuple[float, ...]] = field(default_factory=list)     # Pareto frontier, surplus vectors
	ir_deals: list[Deal] = field(default_factory=list)  # deals that clear every party's threshold (IR set)
	points: dict[str, tuple[float, ...] | None] = field(default_factory=dict)   # named solution points
	descriptors: dict[str, Any] = field(default_factory=dict)
	scale: tuple[float, ...] | None = None              # per-party normalizer (max feasible surplus) for distances
	_surplus_cache: dict[Deal, tuple[float, ...]] = field(default_factory=dict, repr=False)
	# delegation handles set by from_instance so deal-based distances reuse game-theory's exact scale-invariant
	# solutions.distance_to_frontier / distance_to_solution rather than a re-implementation (None for from_sheets)
	_U: Any = field(default=None, repr=False)
	_tau: Any = field(default=None, repr=False)
	_space: Any = field(default=None, repr=False)
	_point_index: dict[str, int] = field(default_factory=dict, repr=False)

	# ------------------------------------------------------------------ surplus --
	def surplus(self, deal_like: Any) -> tuple[float, ...]:
		"""Surplus vector ``(u_i(deal) - tau_i)_i`` for a deal in any accepted form. Computed from the score
		sheets when present (exact for any deal), else looked up in the cached enumeration."""
		deal = self.canonical_deal(deal_like)
		if deal in self._surplus_cache:
			return self._surplus_cache[deal]
		if self.sheets is not None:
			x = tuple(sum(self.sheets[i][j][deal[j]] for j in range(len(self.issues)))
			          - self.thresholds[i] for i in range(self.n_agents))
		else:
			raise KeyError(f"no sheets and deal {deal} not in enumeration cache")
		self._surplus_cache[deal] = x
		return x

	def canonical_deal(self, deal_like: Any) -> Deal:
		"""Map a proposed deal onto ``tuple[int, ...]`` (option index per issue). Accepts an index tuple/list, or
		a ``{issue_name: option}`` dict whose values are option names or indices. Raises ``ValueError`` on an
		incomplete/unknown deal so a malformed proposal is a loud parse failure, not a silent mis-score."""
		if isinstance(deal_like, dict):
			out: list[int] = []
			for name, options in self.issues:
				if name not in deal_like:
					raise ValueError(f"deal missing issue {name!r}: {deal_like}")
				v = deal_like[name]
				if isinstance(v, int):
					out.append(v)
				elif isinstance(v, str):
					if v not in options:
						raise ValueError(f"issue {name!r}: unknown option {v!r} (have {options})")
					out.append(options.index(v))
				else:
					raise ValueError(f"issue {name!r}: bad option value {v!r}")
			return tuple(out)
		deal = tuple(int(v) for v in deal_like)
		if self.issues and len(deal) != len(self.issues):
			raise ValueError(f"deal has {len(deal)} issues, expected {len(self.issues)}")
		return deal

	# ------------------------------------------------------------- distances --
	def distance_to_frontier(self, x: Sequence[float], *, normalized: bool = True) -> float:
		"""Euclidean distance from surplus vector ``x`` to the Pareto frontier (0 if efficient). With
		``normalized`` each coordinate is divided by that party's ``scale`` so parties are commensurable."""
		return S.distance_to_set(x, self.frontier, scale=self.scale if normalized else None)

	def distance_to_point(self, x: Sequence[float], name: str, *, normalized: bool = True) -> float:
		"""Euclidean distance from ``x`` to a named solution point (``nbs``/``ks``/...). ``nan`` if that point
		was not computed for this instance."""
		p = self.points.get(name)
		if p is None:
			return float("nan")
		return S.euclidean(x, p, scale=self.scale if normalized else None)

	def deal_frontier_distance(self, deal_like: Any) -> float:
		"""Scale-invariant distance from a realized deal to the Pareto frontier (0 iff efficient). Delegates to
		game-theory's ``solutions.distance_to_frontier`` (normalized-surplus space) for instances built via
		``from_instance``; falls back to the Euclidean-on-surplus metric for hand-built fixtures."""
		deal = self.canonical_deal(deal_like)
		if self._U is not None and self._space is not None:
			from .. import solutions as _sol
			return float(_sol.distance_to_frontier(self._U, self._tau, self._space.index_of(deal)))
		return self.distance_to_frontier(self.surplus(deal))

	def deal_point_distance(self, deal_like: Any, name: str) -> float:
		"""Scale-invariant distance from a realized deal to a named solution point (``nbs``/``ks``/...).
		Delegates to ``solutions.distance_to_solution`` for ``from_instance`` games, else Euclidean fallback.
		``nan`` if that point was not computed."""
		deal = self.canonical_deal(deal_like)
		ti = self._point_index.get(name)
		if self._U is not None and self._space is not None and ti is not None:
			from .. import solutions as _sol
			return float(_sol.distance_to_solution(self._U, self._tau, self._space.index_of(deal), ti))
		return self.distance_to_point(self.surplus(deal), name)

	# ------------------------------------------------------------ constructors --
	# concept names in game-theory's solutions.py -> this module's point names
	_CONCEPT_MAP = {"nbs": "nash", "ks": "kalai_smorodinsky", "mnw": "max_nash_welfare",
	                "utilitarian": "utilitarian", "egalitarian": "egalitarian"}

	@classmethod
	def from_instance(cls, instance: Any) -> "GameAnalysis":
		"""Build from a stored ``Instance`` (or its ``.to_json()`` dict) whose ``payload`` is a ``GameSpec``.
		Delegates all solving to interlens' ``solutions.py`` (frontier via ``pareto_mask``, points + descriptors
		via ``analyze``, read from ``Instance.solution`` when present, recomputed otherwise). interlens is imported
		lazily so the pure metric math (and ``from_sheets``) never require it."""
		import numpy as np
		from ..sheets import GameSpec
		from .. import solutions as _sol

		payload = instance["payload"] if isinstance(instance, dict) else instance.payload
		solution = (instance.get("solution") if isinstance(instance, dict) else instance.solution) or {}
		# locate the GameSpec dict (scorable tolerates it nested under "game"; the generator packs it as "spec")
		spec_dict = payload.get("game") or payload.get("spec") or payload if isinstance(payload, dict) else payload
		game = GameSpec.from_json(spec_dict)
		issues = [(iss.name, list(iss.options)) for iss in game.space.issues]
		sheets = [[list(row) for row in s.values] for s in game.sheets]
		thresholds = tuple(float(s.threshold) for s in game.sheets)

		U = game.utility_matrix()
		tau = game.thresholds
		X = U - tau
		# merge the precomputed analysis (fuller payload["analysis"] wins over the trimmed Instance.solution),
		# else recompute from the spec — never re-derive if stored.
		analysis: dict = {}
		for cand in (solution, payload.get("analysis") if isinstance(payload, dict) else None):
			if isinstance(cand, dict):
				analysis.update(cand)
		if not analysis.get("solutions"):
			analysis = _sol.analyze(game.space, game.sheets, acceptable_mask=_sol.ir_mask(U, tau))

		frontier = [tuple(float(v) for v in X[int(k)]) for k in np.nonzero(_sol.pareto_mask(U))[0]]
		ir_deals = [game.space.deal_at(int(k)) for k in np.nonzero(_sol.ir_mask(U, tau))[0]]
		sols = analysis.get("solutions", {})
		points = {name: (tuple(float(v) for v in sols[concept]["surpluses"]) if sols.get(concept) else None)
		          for name, concept in cls._CONCEPT_MAP.items()}
		point_index = {name: int(sols[concept]["index"]) for name, concept in cls._CONCEPT_MAP.items()
		               if sols.get(concept) and sols[concept].get("index") is not None}
		ideal = analysis.get("ideal_surplus")
		scale = tuple(max(1.0, float(v)) for v in ideal) if ideal else None
		descriptors = {k: v for k, v in analysis.items() if k != "solutions"}

		ga = cls(n_agents=game.n_parties, thresholds=thresholds, issues=issues, sheets=sheets,
		         frontier=frontier, ir_deals=list(ir_deals), points=points,
		         descriptors=descriptors, scale=scale)
		ga._surplus_cache = {game.space.deal_at(k): tuple(float(v) for v in X[k]) for k in range(int(X.shape[0]))}
		ga._U, ga._tau, ga._space, ga._point_index = U, tau, game.space, point_index
		return ga

	@classmethod
	def from_sheets(cls, sheets: list[list[list[float]]], thresholds: Any, *,
	                issues: list[tuple[str, list[str]]] | None = None,
	                points: dict[str, tuple] | None = None) -> "GameAnalysis":
		"""Enumerate the deal space from raw score sheets and compute the frontier, IR set, welfare argmaxes, and
		descriptors. A self-contained fallback and the tests' constructor — game-theory's ``solutions.py`` is the
		authority for the axiomatic NBS/KS/MNW points, which are only filled here if passed in ``points``."""
		n = len(sheets)
		thresholds = _broadcast_threshold(thresholds, n)
		if issues is None:  # synthesize a schema from the sheet shape
			issues = [(f"I{j}", [f"o{k}" for k in range(len(sheets[0][j]))]) for j in range(len(sheets[0]))]
		n_issues = len(issues)
		deals = list(itertools.product(*[range(len(o)) for _, o in issues]))
		surplus_by_deal = {
			d: tuple(sum(sheets[i][j][d[j]] for j in range(n_issues)) - thresholds[i] for i in range(n))
			for d in deals}
		ir_deals = [d for d, x in surplus_by_deal.items() if all(xi >= 0 for xi in x)]
		frontier = S.pareto_frontier(list(surplus_by_deal.values()))
		# metric-side welfare argmaxes (over the IR set when non-empty, else the whole space)
		pool = ir_deals or deals
		pts: dict[str, tuple | None] = {k: None for k in POINT_NAMES}
		pts["utilitarian"] = surplus_by_deal[max(pool, key=lambda d: S.utilitarian_welfare(surplus_by_deal[d]))]
		pts["egalitarian"] = surplus_by_deal[max(pool, key=lambda d: S.egalitarian_welfare(surplus_by_deal[d]))]
		nash_pool = [d for d in pool if S.nash_welfare(surplus_by_deal[d]) > 0]
		if nash_pool:
			pts["nbs"] = surplus_by_deal[max(nash_pool, key=lambda d: S.nash_welfare(surplus_by_deal[d]))]
		if points:
			pts.update({k: (tuple(v) if v is not None else None) for k, v in points.items()})
		scale = _feasible_scale(surplus_by_deal, ir_deals, n)
		descriptors = _descriptors(surplus_by_deal, ir_deals, frontier, sheets, n_issues)
		ga = cls(n_agents=n, thresholds=thresholds, issues=issues, sheets=sheets,
		         frontier=frontier, ir_deals=ir_deals, points=pts, descriptors=descriptors, scale=scale)
		ga._surplus_cache = surplus_by_deal
		return ga


# ----------------------------------------------------------------------- helpers --
def _broadcast_threshold(thr: Any, n: int) -> tuple[float, ...]:
	"""Per-party thresholds from either a scalar (shared BATNA, the v1 convention) or a length-n sequence."""
	if thr is None:
		return (0.0,) * n
	if isinstance(thr, (int, float)):
		return (float(thr),) * n
	return tuple(float(t) for t in thr)


def _feasible_scale(surplus_by_deal: dict, ir_deals: list, n: int) -> tuple[float, ...]:
	"""Per-party normalizer = that party's max surplus over the feasible (IR) set (or whole space if IR empty),
	floored at 1 so a party with no positive feasible surplus doesn't blow up normalized distances."""
	pool = ir_deals or list(surplus_by_deal)
	return tuple(max(1.0, max(surplus_by_deal[d][i] for d in pool)) for i in range(n))


def _descriptors(surplus_by_deal: dict, ir_deals: list, frontier: list, sheets, n_issues: int) -> dict:
	"""The DESIGN §2.1 score-sheet descriptors: feasibility, Pareto-slack, zero-option sparsity, pairwise IoU."""
	front_set = {tuple(v) for v in frontier}
	ir_on_front = sum(1 for d in ir_deals if surplus_by_deal[d] in front_set)
	n = len(sheets)
	total_opts = sum(len(sheets[0][j]) for j in range(n_issues)) * n
	zeros = sum(1 for i in range(n) for j in range(n_issues) for v in sheets[i][j] if v == 0)
	# pairwise IoU of which (issue,option) cells each party values > 0
	def valued(i):
		return {(j, k) for j in range(n_issues) for k in range(len(sheets[i][j])) if sheets[i][j][k] > 0}
	ious = []
	for i in range(n):
		for j in range(i + 1, n):
			a, b = valued(i), valued(j)
			u = len(a | b)
			ious.append(len(a & b) / u if u else 0.0)
	return {
		"deal_space": len(surplus_by_deal),
		"ir_set_size": len(ir_deals),
		"frontier_size": len(frontier),
		"ir_on_frontier_frac": (ir_on_front / len(ir_deals)) if ir_deals else float("nan"),
		"zero_option_sparsity": zeros / total_opts if total_opts else float("nan"),
		"mean_pairwise_iou": sum(ious) / len(ious) if ious else float("nan"),
	}
