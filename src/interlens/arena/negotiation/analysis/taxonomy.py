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
"""The 12-row LLM-negotiation failure taxonomy as executable checks.

Each check runs over (solved game, parsed episode, oracle annotation) and returns a ``CategoryResult`` (fired,
rate, evidence). Rows are tiered by checkability: Tier 1 mechanical (1,2,6,8,9 — deterministic, though 2/6 need
an acceptance/belief oracle pass and report ``nan`` without one), Tier 2 curve/statistical (3,4,7,10 — from the
concession fits; 10 is cross-condition and defers to ``report.py``), Tier 3 judge-dependent (5,11,12 —
``implemented=False`` stubs with an LLM-judge hook). ``taxonomy_report`` runs every row over one episode;
``TAXONOMY`` is the ordered row list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable

import numpy as np

from . import metrics
from .game_analysis import GameAnalysis
from .episode_view import EpisodeView
from .annotations import EpisodeAnnotation


class Tier(IntEnum):
	MECHANICAL = 1
	CURVE = 2
	JUDGE = 3


# per-row flag ids: annotate.py's mechanical pass writes TurnAnnotation.flags with these, taxonomy reads them.
FLAGS = {
	1: "ir_violation", 2: "deal_closing_bias", 3: "anchoring", 4: "premature_concession",
	5: "preference_action_gap", 6: "belief_miscalibration", 7: "exploration_failure",
	8: "arithmetic_error", 9: "goal_inconsistency", 10: "power_insensitivity",
	11: "manipulation_susceptibility", 12: "tactic_deficit",
}

# the flag strings the oracles emit (into OracleVerdict.flags -> round_checkpoints), mapped to the taxonomy row
# they count for (so a check fires on them as well as on the canonical FLAGS id): threshold -> row 1,
# acceptance -> row 2. (BeliefOracle emits no flag — row 6 compares stated belief to verdict.beliefs.)
ORACLE_FLAGS = {
	"below_threshold_accept": 1, "below_threshold_propose": 1,
	"premature_accept": 2, "should_accept": 2, "deadline_brinkmanship": 2,
}


def _row_flag_strings(row: int) -> set[str]:
	"""All flag strings that count for a taxonomy row: the canonical FLAGS id plus the oracle-emitted strings."""
	return {FLAGS[row]} | {f for f, r in ORACLE_FLAGS.items() if r == row}


@dataclass
class CategoryResult:
	"""Outcome of one taxonomy check on one episode."""

	category_id: int
	name: str
	tier: Tier
	fired: bool
	rate: float                     # fraction exhibiting the failure (nan if undefined / needs an oracle)
	evidence: list[dict] = field(default_factory=list)
	implemented: bool = True        # False for tier-3 stubs and cross-condition rows
	note: str = ""

	def to_json(self) -> dict:
		return {"category_id": self.category_id, "name": self.name, "tier": int(self.tier),
		        "fired": self.fired, "rate": self.rate, "n_evidence": len(self.evidence),
		        "evidence": self.evidence[:20], "implemented": self.implemented, "note": self.note}


# ------------------------------------------------------------- annotation helpers --
def _flagged_turns(annotation: EpisodeAnnotation | None, row: int) -> list[dict]:
	"""Turns whose annotation carries any flag string for this row — the canonical FLAGS id (mechanical pass) or
	an oracle-emitted string, per ``_row_flag_strings``."""
	if annotation is None:
		return []
	want = _row_flag_strings(row)
	return [{"turn_idx": t.turn_idx, "seat": t.seat, "regret": t.regret}
	        for t in annotation.turns if want & set(t.flags)]


# =============================================================== Tier-1 checks ==
def check_ir_violation(game, view, annotation) -> CategoryResult:
	viols = metrics.ir_violations(game, view)
	n_actions = sum(1 for t in view.turns if t.proposed_deal is not None or t.accepted_offer_id is not None)
	rate = (len(viols) / n_actions) if n_actions else float("nan")
	return CategoryResult(1, "Dominated-offer acceptance / IR violation", Tier.MECHANICAL,
	                      fired=bool(viols), rate=rate, evidence=viols,
	                      note="fully mechanical (own-surplus < 0 on propose/accept)")


def check_deal_closing(game, view, annotation) -> CategoryResult:
	ev = _flagged_turns(annotation, 2)
	n_acc = sum(1 for t in view.turns if t.accepted_offer_id is not None)
	if annotation is None:
		return CategoryResult(2, "Deal-closing / agreement bias", Tier.MECHANICAL, fired=False,
		                      rate=float("nan"), implemented=True,
		                      note="mechanical given the acceptance oracle; run annotate.py to populate "
		                           "(accept when EV(accept) < continuation value)")
	rate = (len(ev) / n_acc) if n_acc else float("nan")
	return CategoryResult(2, "Deal-closing / agreement bias", Tier.MECHANICAL, fired=bool(ev), rate=rate,
	                      evidence=ev, note="accept flagged against the acceptance oracle (accept-vs-continue)")


def check_belief_miscalibration(game, view, annotation) -> CategoryResult:
	ev = _flagged_turns(annotation, 6)
	cal = metrics.belief_calibration(annotation)
	if annotation is None or cal["n"] == 0:
		return CategoryResult(6, "Belief-update / calibration failure", Tier.MECHANICAL, fired=False,
		                      rate=float("nan"), implemented=True,
		                      note="mechanical given the BeliefOracle posterior; needs stated-belief notes + a "
		                           "belief-oracle annotation pass")
	return CategoryResult(6, "Belief-update / calibration failure", Tier.MECHANICAL, fired=bool(ev),
	                      rate=cal["mean_l1"], evidence=ev,
	                      note=f"mean L1 stated-vs-posterior over {cal['n']} turns")


def check_arithmetic_error(game, view, annotation) -> CategoryResult:
	"""Recompute a party's stated own-score for a deal against the true score sheet. Mechanical when the action
	schema carries a machine-readable ``stated_score``; annotation flags (written by an oracle pass that parsed
	the CoT) are also honored."""
	ev = list(_flagged_turns(annotation, 8))
	tol = 1e-6
	n_checked = 0
	for t in view.turns:
		si = view.seat_index(t.seat) if t.seat in view.seats else None
		raw = t.raw_action if isinstance(t.raw_action, dict) else {}
		stated = raw.get("stated_score", raw.get("stated_utility"))
		if si is None or stated is None or t.proposed_deal is None:
			continue
		n_checked += 1
		true_util = game.surplus(t.proposed_deal)[si] + game.thresholds[si]
		if abs(float(stated) - true_util) > tol:
			ev.append({"turn_idx": t.idx, "seat": t.seat, "stated": float(stated), "true": true_util})
	rate = (len(ev) / n_checked) if n_checked else float("nan")
	return CategoryResult(8, "Arithmetic / utility-computation error", Tier.MECHANICAL, fired=bool(ev),
	                      rate=rate, evidence=ev,
	                      note="mechanical when a stated_score/utility field is present; else set by an "
	                           "oracle CoT-parse pass")


def check_goal_inconsistency(game, view, annotation) -> CategoryResult:
	"""A party's stated acceptable-offer floor drifts with no new incoming offer since its last statement
	(Davidson 2024: target/limit drifts without new information). Mechanical proxy over the stated-offer notes."""
	ev = list(_flagged_turns(annotation, 9))
	others_proposals_before = _other_proposals_before(view)
	for seat in view.seats:
		si = view.seat_index(seat)
		last_floor, last_seen_other = None, -1
		for t in view.turns:
			if t.seat != seat or t.stated_offer is None:
				continue
			floor = game.surplus(t.stated_offer)[si]
			seen_other = others_proposals_before[t.idx]
			if last_floor is not None and abs(floor - last_floor) > 1e-6 and seen_other == last_seen_other:
				ev.append({"turn_idx": t.idx, "seat": seat, "from_floor": last_floor, "to_floor": floor,
				           "new_info": False})
			last_floor, last_seen_other = floor, seen_other
	return CategoryResult(9, "Goal inconsistency across turns", Tier.MECHANICAL, fired=bool(ev),
	                      rate=float(len(ev)), evidence=ev,
	                      note="mechanical proxy: stated-floor drift with no intervening counterpart proposal")


def _other_proposals_before(view: EpisodeView) -> dict[int, int]:
	"""For each turn idx, how many proposals by OTHER seats had been made strictly before it — the 'new info'
	clock used by the goal-inconsistency check (a party's own proposals are not new information to itself)."""
	props = [(t.idx, t.seat) for t in view.turns if t.proposed_deal is not None]
	return {t.idx: sum(1 for (pi, ps) in props if pi < t.idx and ps != t.seat) for t in view.turns}


# =============================================================== Tier-2 checks ==
def check_anchoring(game, view, annotation) -> CategoryResult:
	"""Rigid extreme anchoring: a party makes >=2 offers whose own-surplus barely moves (range below 5% of its
	feasible scale) or fits a near-vertical/degenerate concession curve. Read from the concession fits."""
	fits = metrics.concession_fits(game, view)
	ev = []
	for seat, fit in fits.items():
		si = view.seat_index(seat)
		series = [game.surplus(t.proposed_deal)[si] for t in view.proposals_by(seat)]
		if len(series) < 2:
			continue
		scale = game.scale[si] if game.scale else max(1.0, max(abs(s) for s in series))
		rng = (max(series) - min(series)) / scale
		if rng < 0.05:
			ev.append({"seat": seat, "own_surplus_range_frac": rng, "n_offers": len(series),
			           "cri": fit.cri})
	return CategoryResult(3, "Anchoring (rigid extreme anchoring)", Tier.CURVE, fired=bool(ev),
	                      rate=float(len(ev)), evidence=ev,
	                      note="per-episode proxy from concession fits; first-offer→final-price correlation is "
	                           "cross-episode (see report.py anchoring_correlation)")


def check_premature_concession(game, view, annotation) -> CategoryResult:
	"""Excess/early concession: a party gives up a large fraction of its own surplus across its offers (high
	burstiness τ with a downward step), especially early. Read from the concession fits (τ, CRI) and the
	own-surplus drop."""
	fits = metrics.concession_fits(game, view)
	ev = []
	for seat, fit in fits.items():
		si = view.seat_index(seat)
		series = [game.surplus(t.proposed_deal)[si] for t in view.proposals_by(seat)]
		if len(series) < 3:
			continue
		scale = game.scale[si] if game.scale else max(1.0, max(abs(s) for s in series))
		drop = (series[0] - series[-1]) / scale       # positive = conceded own surplus
		if drop > 0.5:
			ev.append({"seat": seat, "own_surplus_drop_frac": drop, "tau": fit.tau, "cri": fit.cri})
	return CategoryResult(4, "Premature / excess concession", Tier.CURVE, fired=bool(ev), rate=float(len(ev)),
	                      evidence=ev, note="proxy: own-surplus drop > 50% of feasible scale across offers; "
	                                        "τ/CRI reported per party in metrics.concession")


def check_exploration_failure(game, view, annotation) -> CategoryResult:
	"""Commits (first accept / final proposal) before gathering information: accepts within the first two turns
	with no prior counter-proposal from others (multi-buyer 'fails to explore the pool')."""
	ev = []
	first_other_prop = min((t.idx for t in view.turns if t.proposed_deal is not None), default=None)
	for t in view.turns:
		if t.accepted_offer_id is None:
			continue
		prior_props = sum(1 for u in view.turns if u.idx < t.idx and u.proposed_deal is not None
		                  and u.seat != t.seat)
		if t.round <= 1 and prior_props == 0:
			ev.append({"turn_idx": t.idx, "seat": t.seat, "round": t.round, "prior_other_proposals": 0})
		break  # only the first commit matters for exploration
	return CategoryResult(7, "Exploration / screening failure", Tier.CURVE, fired=bool(ev),
	                      rate=float(len(ev)), evidence=ev,
	                      note="proxy: early commit with no prior counterpart proposal; sharp version needs a "
	                           "probing/information-value oracle")


def check_power_insensitivity(game, view, annotation) -> CategoryResult:
	"""Identical strategy across power-asymmetry conditions where the oracle strategy differs — inherently
	CROSS-condition. Cannot fire on a single episode; ``report.py`` computes it across matched arms."""
	return CategoryResult(10, "Power / context insensitivity", Tier.CURVE, fired=False, rate=float("nan"),
	                      implemented=False,
	                      note="cross-condition: computed in report.py by comparing a model's offer trajectory "
	                           "across power/asymmetry arms against the oracle's differing strategies")


# =============================================================== Tier-3 stubs ==
def _judge_stub(row: int, name: str, note: str) -> CategoryResult:
	return CategoryResult(row, name, Tier.JUDGE, fired=False, rate=float("nan"), implemented=False, note=note)


def check_preference_action_gap(game, view, annotation) -> CategoryResult:
	"""STUB (Tier 3). Correct opponent-preference inference in the CoT but the offer is unchanged vs the
	best-response oracle (Counterparty Modeling, arXiv:2605.16575). Hook: an LLM judge extracts the inferred
	opponent preference from ``TurnView.thinking``; compare the made offer to the BestResponseOracle action
	given that (correct) inference. Fires when inference is correct but the action does not move toward BR."""
	return _judge_stub(5, "Preference-action gap",
	                   "future: LLM-judge extracts CoT preference inference; compare vs BestResponseOracle "
	                   "(annotation.oracle['bestresponse']) — flag correct-inference + unchanged-offer")


def check_manipulation_susceptibility(game, view, annotation) -> CategoryResult:
	"""STUB (Tier 3). Outcome delta when the counterpart uses scripted pressure tactics (NegotiationArena;
	converges with the conv_dataset confidence-vs-logic finding). Hook: paired ±scripted-adversary arms; the
	report contrasts the party's surplus/capitulation with vs without the pressure participant."""
	return _judge_stub(11, "Manipulation susceptibility",
	                   "future: cross-arm contrast (±scripted-pressure counterpart) computed in report.py; "
	                   "per-turn capitulation optionally judged from thinking")


def check_tactic_deficit(game, view, annotation) -> CategoryResult:
	"""STUB (Tier 3). Tactic-frequency profile vs successful humans (Diplomacy tactic taxonomy,
	arXiv:2512.18292). Hook: an LLM tactic classifier (validated to Gwet's AC1 >= 0.65) labels each message with
	the 8-tactic scheme; compare the frequency profile to a human reference."""
	return _judge_stub(12, "Tactic-style deficits",
	                   "future: LLM tactic classifier (8-tactic Ethos/Pathos/Logos scheme) on messages; compare "
	                   "frequency profile to a successful-human reference, validated by Gwet's AC1")


# ------------------------------------------------------------------ registry --
TAXONOMY: list[tuple[int, str, Tier, list[str], Callable]] = [
	(1, "Dominated-offer acceptance / IR violation", Tier.MECHANICAL,
	 ["Davidson 2024 (2401.04536)", "Bilateral-trade 2604.16472 (NGFT)", "TERMS-Bench 2605.13909"], check_ir_violation),
	(2, "Deal-closing / agreement bias", Tier.MECHANICAL,
	 ["Bilateral-trade 2604.16472 (RL amplifies)", "Davidson 2024"], check_deal_closing),
	(3, "Anchoring (susceptibility + rigid extreme anchoring)", Tier.CURVE,
	 ["LLM Rationalis 2512.13063", "Anchoring 2508.21137", "Counterparty 2605.16575"], check_anchoring),
	(4, "Premature / excess concession, agreeableness", Tier.CURVE,
	 ["LLM Rationalis 2512.13063 (τ, CRI)", "Counterparty 2605.16575", "Davidson 2024"], check_premature_concession),
	(5, "Preference-action gap", Tier.JUDGE,
	 ["Counterparty Modeling 2605.16575"], check_preference_action_gap),
	(6, "Belief-update / calibration failure", Tier.MECHANICAL,
	 ["TERMS-Bench 2605.13909", "Are-LLMs-Effective-Negotiators 2402.13550"], check_belief_miscalibration),
	(7, "Exploration / screening failure", Tier.CURVE,
	 ["Multi-buyer RLVR 2607.05863"], check_exploration_failure),
	(8, "Arithmetic / utility-computation error", Tier.MECHANICAL,
	 ["Are-LLMs-Effective-Negotiators 2402.13550", "GTBench 2402.12348"], check_arithmetic_error),
	(9, "Goal inconsistency across turns", Tier.MECHANICAL,
	 ["Davidson 2024 (2401.04536)"], check_goal_inconsistency),
	(10, "Power / context insensitivity", Tier.CURVE,
	 ["LLM Rationalis 2512.13063 (6 power scenarios)", "STEER-ME 2502.13119"], check_power_insensitivity),
	(11, "Susceptibility to adversarial tactics / manipulation", Tier.JUDGE,
	 ["NegotiationArena 2402.05863", "conv_dataset confidence-vs-logic"], check_manipulation_susceptibility),
	(12, "Tactic-style deficits (rapport, indirect persuasion)", Tier.JUDGE,
	 ["Diplomacy tactics 2512.18292"], check_tactic_deficit),
]


def taxonomy_report(game: GameAnalysis, view: EpisodeView,
                    annotation: EpisodeAnnotation | None = None) -> list[CategoryResult]:
	"""Run every taxonomy row over one episode, in row order."""
	return [check(game, view, annotation) for (_id, _name, _tier, _cites, check) in TAXONOMY]


def taxonomy_rows() -> list[dict]:
	"""The taxonomy as a static table (id, name, tier, citations, implemented) for docs/report headers."""
	stubs = {5, 10, 11, 12}
	return [{"id": i, "name": n, "tier": int(t), "tier_name": t.name.lower(), "citations": c,
	         "implemented": i not in stubs} for (i, n, t, c, _check) in TAXONOMY]
