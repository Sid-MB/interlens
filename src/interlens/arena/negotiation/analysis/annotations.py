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
"""Per-turn annotation records: the divergence data model ``annotate.py`` writes and ``taxonomy.py`` /
``report.py`` read (disk I/O lives in ``runio.AnnotationStore``).

An ``EpisodeAnnotation`` is one episode's divergence record — a ``TurnAnnotation`` per turn (oracle verdicts,
headline regret, hard-violation flags, counterfactual regret, CoT first-divergent-step) plus a rolled-up
``DivergenceSummary`` — kept separate from the immutable raw ``Episode`` so re-annotating never rewrites it.
``TurnAnnotation.oracle`` mirrors interlens' per-oracle ``OracleRecord`` (name → verdict).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class TurnAnnotation:
	"""One turn's oracle annotation. ``oracle`` maps an oracle name to its verdict dict
	(``{best, best_value, chosen_value, regret, beliefs?, flags?}``); ``regret`` is the headline per-turn
	surplus-loss from the primary value oracle; ``flags`` are the taxonomy row ids that fired this turn."""

	turn_idx: int
	round: int
	seat: str
	oracle: dict[str, dict] = field(default_factory=dict)
	regret: float | None = None
	flags: list[str] = field(default_factory=list)
	cf_regret: float | None = None            # counterfactual k-rollout regret (frozen counterparts), if computed
	cot_first_divergent_step: int | None = None
	oracle_belief: Any = None                 # oracle posterior at this turn (belief-calibration reference)
	stated_belief: Any = None                 # the model's stated belief (calibration comparison)

	def to_json(self) -> dict:
		return asdict(self)

	@staticmethod
	def from_json(d: dict) -> "TurnAnnotation":
		return TurnAnnotation(**d)


@dataclass
class DivergenceSummary:
	"""Episode-level roll-up of the turn annotations: the regret series and its aggregates, the divergence-point
	turns (regret above the noise threshold), and hard-flag counts by taxonomy row."""

	episode_id: str
	model: str
	arm: str
	n_turns: int
	n_flagged: int
	regret_series: list[float]
	mean_regret: float
	total_regret: float
	divergence_turns: list[int]
	flag_counts: dict[str, int]
	outcome: dict = field(default_factory=dict)

	def to_json(self) -> dict:
		return asdict(self)

	@staticmethod
	def from_json(d: dict) -> "DivergenceSummary":
		return DivergenceSummary(**d)


@dataclass
class EpisodeAnnotation:
	"""One episode's full divergence record: the summary plus every turn annotation."""

	episode_id: str
	summary: DivergenceSummary
	turns: list[TurnAnnotation] = field(default_factory=list)

	def to_json(self) -> dict:
		return {"episode_id": self.episode_id, "summary": self.summary.to_json(),
		        "turns": [t.to_json() for t in self.turns]}

	@staticmethod
	def from_json(d: dict) -> "EpisodeAnnotation":
		return EpisodeAnnotation(episode_id=d["episode_id"],
		                         summary=DivergenceSummary.from_json(d["summary"]),
		                         turns=[TurnAnnotation.from_json(t) for t in d.get("turns", [])])


# preference order for the "primary" per-turn regret oracle: the headline surplus-loss is the best-response /
# equilibrium oracle, then acceptance, then solution — first present wins.
PRIMARY_ORACLES = ("bestresponse", "best_response", "equilibrium", "acceptance", "solution")


def summarize_turns(episode_id: str, model: str, arm: str, outcome: dict,
                    turn_anns: list[TurnAnnotation], threshold: float) -> DivergenceSummary:
	"""Roll a list of turn annotations up into a ``DivergenceSummary`` (shared by ``annotate.py`` and the
	inline-rows reader so the summary math lives in one place)."""
	regret_series = [float(t.regret) if t.regret is not None else 0.0 for t in turn_anns]
	div_turns = [t.turn_idx for t in turn_anns if (t.regret or 0.0) > threshold]
	flag_counts: dict[str, int] = {}
	for t in turn_anns:
		for f in t.flags:
			flag_counts[f] = flag_counts.get(f, 0) + 1
	return DivergenceSummary(
		episode_id=episode_id, model=model, arm=arm, n_turns=len(turn_anns),
		n_flagged=sum(1 for t in turn_anns if t.flags), regret_series=regret_series,
		mean_regret=(sum(regret_series) / len(regret_series)) if regret_series else 0.0,
		total_regret=sum(regret_series), divergence_turns=div_turns, flag_counts=flag_counts,
		outcome=outcome)


def _extra_scalar(extra) -> float | None:
	"""A scalar per-turn loss read out of an oracle verdict's ``extra`` diagnostics.

	``extra`` is a free-form per-oracle payload, so this reads the first numeric under any of a few known keys
	rather than assuming one schema — a best-response oracle reports ``surplus_loss``, others ``regret``. Used
	only as the fallback when a row carries no ``divergence`` of its own."""
	if isinstance(extra, dict):
		for k in ("surplus_loss", "regret", "chosen_surplus_loss"):
			v = extra.get(k)
			if isinstance(v, (int, float)):
				return float(v)
	return None


def _row_regret(row: dict) -> float | None:
	"""Per-turn regret from one inline oracle row: the canonical ``divergence`` (best_value − chosen_value), or,
	when that is absent, a scalar loss carried in ``verdict.extra``."""
	d = row.get("divergence")
	if d is not None:
		return float(d)
	return _extra_scalar((row.get("verdict") or {}).get("extra"))


def inline_oracle_rows(episode: dict) -> list[dict]:
	"""The episode's INLINE oracle annotation rows in ``round_checkpoints`` — the ``OracleRecord.to_json()``
	dicts, identified by a ``"verdict"`` key (forked provisional-probe rows have no verdict and are excluded)."""
	return [r for r in (episode.get("round_checkpoints") or []) if isinstance(r, dict) and "verdict" in r]


def group_oracle_rows(rows: list[dict], *, primary: tuple = PRIMARY_ORACLES) -> list[dict]:
	"""Group inline oracle rows by turn into ``[{turn_idx, round, seat, oracle:{name:row}, regret, flags,
	belief}]`` (turn order). The per-turn ``regret`` is the ``divergence`` of the first oracle in ``primary``
	present, else the max-divergence oracle; ``flags`` are unioned across that turn's oracles. Shared by
	``annotation_from_episode`` and ``annotate.py``'s inline merge."""
	by_turn: dict = {}
	for r in rows:
		ti = r.get("turn_idx")
		key = ti if isinstance(ti, int) and ti >= 0 else (r.get("round"), r.get("seat"))
		by_turn.setdefault(key, []).append(r)
	out = []
	for key in sorted(by_turn, key=lambda k: k if isinstance(k, int) else 1 << 30):
		group = by_turn[key]
		oracle = {r.get("oracle", "?"): r for r in group}
		prow = next((oracle[n] for n in primary if n in oracle), None) \
			or max(group, key=lambda r: (_row_regret(r) or 0.0))
		ti = prow.get("turn_idx", -1)
		out.append({
			"turn_idx": ti if isinstance(ti, int) and ti >= 0 else (key if isinstance(key, int) else -1),
			"round": prow.get("round", 0), "seat": prow.get("seat", ""), "oracle": oracle,
			"regret": _row_regret(prow), "flags": sorted({f for r in group for f in (r.get("flags") or [])}),
			"belief": next(((r.get("verdict") or {}).get("beliefs") for r in group
			                if (r.get("verdict") or {}).get("beliefs") is not None), None)})
	return out


def annotation_from_episode(episode: dict, *, threshold: float = 1e-6) -> "EpisodeAnnotation | None":
	"""Build an ``EpisodeAnnotation`` purely from an episode's inline oracle rows (``round_checkpoints``).

	Returns ``None`` when the episode carries no inline oracle rows (a v0 dataset or a not-yet-annotated run), so
	callers fall back to the mechanical-only path. Used by ``report.py`` to show oracle regret straight from a
	stored run without a separate annotate pass."""
	rows = inline_oracle_rows(episode)
	if not rows:
		return None
	turn_anns = [TurnAnnotation(turn_idx=g["turn_idx"], round=g["round"], seat=g["seat"], oracle=g["oracle"],
	                            regret=g["regret"], flags=list(g["flags"]), oracle_belief=g["belief"])
	             for g in group_oracle_rows(rows)]
	summary = summarize_turns(episode.get("episode_id", ""), episode.get("model", ""),
	                          episode.get("arm", ""), episode.get("outcome") or {}, turn_anns, threshold)
	return EpisodeAnnotation(episode_id=episode.get("episode_id", ""), summary=summary, turns=turn_anns)
