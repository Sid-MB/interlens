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
"""The divergence metric suite: outcome-, turn-, and faithfulness-level measures over one episode.

Pure functions of a solved game (``GameAnalysis``), the parsed episode (``EpisodeView``), and — for the
regret/belief measures — the oracle annotations (``EpisodeAnnotation``). Composes the ``surplus`` and ``curves``
math layers (never re-derives); ``taxonomy.py`` and ``report.py`` call these. Groups: ``outcome_metrics``
(deal, surplus, distance-to-frontier/NBS/KS, USW/ESW/NSW/Gini, U vs U*, welfare trajectory); turn-level
primitives (regret series + no-regret tests, the mechanical IR/dominated detectors, concession fits); and
faithfulness (stated-offer vs offers made, stated-belief vs oracle posterior). Every function degrades to
``nan``/empty rather than raising when an input (a solution point, an annotation) is absent.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import surplus as S
from . import curves
from .game_analysis import GameAnalysis
from .episode_view import EpisodeView, TurnView
from .annotations import EpisodeAnnotation

# turns whose per-turn regret exceeds this (surplus units) are counted as divergence points — mismatch alone
# over-labels since several actions are often near-optimal (DESIGN §5 / divergence-training §pipeline-a2)
DEFAULT_REGRET_THRESHOLD = 1e-6


# ============================================================= outcome level ==
def outcome_metrics(game: GameAnalysis, view: EpisodeView) -> dict:
	"""Outcome-level divergence for one episode. On a no-deal episode the welfare fields are 0 (USW/ESW/NSW) and
	Gini is ``nan`` (no distribution), while ``surplus`` is ``None`` — this is the U-vs-U* distinction: the
	unconditional welfare counts no-deal as 0, the conditional (``*_conditional``) is ``None`` and excluded from
	deal-only aggregates upstream."""
	x = game.surplus(view.final_deal) if view.final_deal is not None else None
	reached = view.reached and x is not None
	out: dict[str, Any] = {
		"deal_reached": bool(reached),
		"surplus": list(x) if x is not None else None,
	}
	if reached:
		df = game.deal_frontier_distance(view.final_deal)   # scale-invariant (game-theory) for real instances
		out.update({
			"dist_to_frontier": df,
			"dist_to_nbs": game.deal_point_distance(view.final_deal, "nbs"),
			"dist_to_ks": game.deal_point_distance(view.final_deal, "ks"),
			"usw": S.utilitarian_welfare(x),
			"esw": S.egalitarian_welfare(x),
			"nsw": S.nash_welfare(x),                    # raw product (kept in atlas.json)
			"nsw_geomean": S.nash_welfare_geomean(x),    # display form: geometric mean of surpluses
			"gini": S.gini(x),
			"on_frontier": df <= DEFAULT_REGRET_THRESHOLD,
			"all_ir": all(xi >= 0 for xi in x),
		})
		# U (unconditional) counts this deal's welfare; U* (conditional) is the same when reached
		out["usw_unconditional"] = S.utilitarian_welfare(x)
		out["usw_conditional"] = S.utilitarian_welfare(x)
	else:
		out.update({"dist_to_frontier": float("nan"), "dist_to_nbs": float("nan"),
		            "dist_to_ks": float("nan"), "usw": 0.0, "esw": 0.0, "nsw": 0.0,
		            "nsw_geomean": 0.0, "gini": float("nan"), "on_frontier": False, "all_ir": False,
		            "usw_unconditional": 0.0, "usw_conditional": None})
	out["welfare_trajectory"] = welfare_trajectory(game, view)
	return out


def welfare_trajectory(game: GameAnalysis, view: EpisodeView) -> dict:
	"""Per-round utilitarian welfare of the standing (tabled) deal, with an OLS slope and variance. A negative
	slope = deals get collectively *worse* over rounds (Study B: Phi-3.5 USW slope −5.8); high variance = the
	table thrashes. ``nan`` slope when fewer than two rounds carry a standing offer."""
	rounds = sorted(view.standing_offer_by_round)
	xs, ys = [], []
	for r in rounds:
		deal = view.standing_offer_by_round[r]
		if deal is None:
			continue
		xs.append(r)
		ys.append(S.utilitarian_welfare(game.surplus(deal)))
	if len(ys) < 2:
		return {"rounds": xs, "usw_by_round": ys, "slope": float("nan"),
		        "variance": float(np.var(ys)) if ys else float("nan")}
	slope = float(np.polyfit(xs, ys, 1)[0])
	return {"rounds": xs, "usw_by_round": ys, "slope": slope, "variance": float(np.var(ys))}


# ============================================== turn-level: mechanical detectors ==
def ir_violations(game: GameAnalysis, view: EpisodeView) -> list[dict]:
	"""Turns on which a party proposed or accepted a deal scoring below its OWN threshold (surplus < 0) — the
	individual-rationality / 'wrong deal' failure (Abdelnabi wrong-deal rate 7–20%; multi-buyer sell-below-cost
	up to 38.3%). Fully mechanical: reads the acting party's surplus off the score sheet."""
	out = []
	for t in view.turns:
		si = view.seat_index(t.seat) if t.seat in view.seats else None
		if si is None:
			continue
		if t.proposed_deal is not None:
			own = game.surplus(t.proposed_deal)[si]
			if own < 0:
				out.append({"turn_idx": t.idx, "seat": t.seat, "kind": "propose",
				            "own_surplus": own, "deal": list(t.proposed_deal)})
		if t.accepted_offer_id is not None and t.accepted_offer_id in view.proposals:
			deal = view.proposals[t.accepted_offer_id]["deal"]
			own = game.surplus(deal)[si]
			if own < 0:
				out.append({"turn_idx": t.idx, "seat": t.seat, "kind": "accept",
				            "own_surplus": own, "deal": list(deal)})
	return out


def dominated_proposals(game: GameAnalysis, view: EpisodeView) -> list[dict]:
	"""Turns on which the proposed deal is Pareto-dominated — a strictly-better-for-everyone alternative existed.
	Reports both dominance vs the Pareto frontier and, more sharply, vs the IR (feasible) set (a Pareto
	improvement everyone would have accepted). Mechanical."""
	ir_surplus = [game.surplus(d) for d in game.ir_deals]
	out = []
	for t in view.turns:
		if t.proposed_deal is None:
			continue
		x = game.surplus(t.proposed_deal)
		dom_front = S.dominating_alternatives(x, game.frontier)
		dom_feasible = S.dominating_alternatives(x, ir_surplus)
		if dom_front:
			out.append({"turn_idx": t.idx, "seat": t.seat, "deal": list(t.proposed_deal),
			            "surplus": list(x), "dominated_vs_frontier": True,
			            "dominated_by_feasible": bool(dom_feasible),
			            "n_dominating_feasible": len(dom_feasible)})
	return out


def concession_fits(game: GameAnalysis, view: EpisodeView) -> dict[str, curves.ConcessionFit]:
	"""Per-party concession-curve fit on the sequence of the party's OWN surplus across its OWN successive
	proposals (the offers it puts on the table). Parties with < 3 proposals get an ``n<3`` fit with ``nan``
	shape metrics. Read τ (burstiness) and CRI (rigidity) off each fit."""
	fits: dict[str, curves.ConcessionFit] = {}
	for seat in view.seats:
		si = view.seat_index(seat)
		own_series = [game.surplus(t.proposed_deal)[si] for t in view.proposals_by(seat)]
		if own_series:
			fits[seat] = curves.fit_concession_curve(own_series)
	return fits


# ============================================== turn-level: regret / no-regret ==
def regret_series(annotation: EpisodeAnnotation | None) -> list[float]:
	"""The per-turn headline regret series (surplus loss) from an annotation, 0.0 where a turn has no recorded
	regret. Empty when there is no annotation (no oracle pass has been run)."""
	if annotation is None:
		return []
	return [float(t.regret) if t.regret is not None else 0.0 for t in annotation.turns]


def no_regret_tests(annotation: EpisodeAnnotation | None) -> dict:
	"""Park no-regret trend + log–log tests over the per-turn regret series. Returns ``None`` fields when there
	is no annotation or the series is too short."""
	series = regret_series(annotation)
	if len(series) < 3:
		return {"trend": None, "loglog": None, "n": len(series)}
	return {"trend": curves.no_regret_trend_test(series).to_json(),
	        "loglog": curves.loglog_regret_slope(series).to_json(), "n": len(series)}


def divergence_turns(annotation: EpisodeAnnotation | None,
                     threshold: float = DEFAULT_REGRET_THRESHOLD) -> list[int]:
	"""Turn indices whose per-turn regret exceeds ``threshold`` — the localized divergence points."""
	if annotation is None:
		return []
	return [t.turn_idx for t in annotation.turns if (t.regret or 0.0) > threshold]


# ==================================================== faithfulness / calibration ==
def stated_offer_faithfulness(game: GameAnalysis, view: EpisodeView) -> dict:
	"""Internal faithfulness (LAMEN, Davidson 2024): are a party's actual proposals consistent with its own
	machine-readable 'currently acceptable offer' note? For each proposal made after the party states an
	acceptable offer, faithful iff the proposal is at least as good for the party as its stated floor
	(own-surplus(proposal) >= own-surplus(stated floor) − ε). Returns the overall rate and per-party rates; the
	rate is ``nan`` when the scenario elicits no acceptable-offer note (none of the turns carry ``stated_offer``)."""
	eps = 1e-9
	per_party: dict[str, list[bool]] = {}
	for seat in view.seats:
		si = view.seat_index(seat)
		floor: float | None = None
		checks: list[bool] = []
		for t in view.turns:
			if t.seat != seat:
				continue
			if t.stated_offer is not None:
				floor = game.surplus(t.stated_offer)[si]
			if t.proposed_deal is not None and floor is not None:
				own = game.surplus(t.proposed_deal)[si]
				checks.append(own >= floor - eps)
		if checks:
			per_party[seat] = checks
	all_checks = [c for cs in per_party.values() for c in cs]
	rate = float(np.mean(all_checks)) if all_checks else float("nan")
	return {"rate": rate, "n": len(all_checks),
	        "per_party": {s: float(np.mean(cs)) for s, cs in per_party.items()}}


def belief_calibration(annotation: EpisodeAnnotation | None) -> dict:
	"""Belief-calibration error: mean L1 distance between the model's stated belief and the oracle posterior over
	the turns where both are present, when both are numeric vectors/distributions. ``nan`` when the scenario
	elicits no beliefs or the oracle recorded none (belief calibration is the BeliefOracle-dependent metric)."""
	if annotation is None:
		return {"mean_l1": float("nan"), "n": 0}
	dists = []
	for t in annotation.turns:
		a, b = t.stated_belief, t.oracle_belief
		v = _belief_l1(a, b)
		if v is not None:
			dists.append(v)
	return {"mean_l1": float(np.mean(dists)) if dists else float("nan"), "n": len(dists)}


def _belief_l1(stated: Any, oracle: Any) -> float | None:
	"""L1 distance between two belief distributions given as equal-length numeric sequences or dicts over shared
	keys; ``None`` if they are not comparable numeric distributions."""
	if stated is None or oracle is None:
		return None
	try:
		if isinstance(stated, dict) and isinstance(oracle, dict):
			keys = set(stated) | set(oracle)
			return float(sum(abs(float(stated.get(k, 0.0)) - float(oracle.get(k, 0.0))) for k in keys))
		a = np.asarray(stated, dtype=float).ravel()
		b = np.asarray(oracle, dtype=float).ravel()
		if a.shape != b.shape or a.size == 0:
			return None
		return float(np.abs(a - b).sum())
	except (TypeError, ValueError):
		return None


# ================================================================== full bundle ==
def episode_metrics(game: GameAnalysis, view: EpisodeView,
                    annotation: EpisodeAnnotation | None = None) -> dict:
	"""All divergence metrics for one episode, in one dict — the row the atlas aggregates over."""
	return {
		"episode_id": view.episode_id,
		"model": view.model,
		"arm": view.arm,
		"outcome": outcome_metrics(game, view),
		"turn": {
			"ir_violations": ir_violations(game, view),
			"dominated_proposals": dominated_proposals(game, view),
			"concession": {s: f.to_json() for s, f in concession_fits(game, view).items()},
			"regret_series": regret_series(annotation),
			"no_regret": no_regret_tests(annotation),
			"divergence_turns": divergence_turns(annotation),
		},
		"faithfulness": {
			"stated_offer": stated_offer_faithfulness(game, view),
			"belief_calibration": belief_calibration(annotation),
		},
	}
