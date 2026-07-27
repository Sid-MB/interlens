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

# [rational_agents scaffold: interlens-core] 2026-07-23

"""The oracle layer: per-turn "what would a rational agent have done here?" annotations.

An ``Oracle`` scores every action available to a seat at a decision point and names the best one; the arena
then measures the seat's *regret* — ``value(best) - value(chosen)`` in the game's value units — the
centipawn-loss analog for negotiation (Regan & Haworth 2011). Oracles compose: a solution oracle, a belief
oracle, an acceptance oracle, an equilibrium oracle, each citing its own literature — those concrete
negotiation oracles live in ``interlens.arena.negotiation`` and subclass this generic ``Oracle`` ABC.

Two annotation paths write into an episode's oracle log, both typed as :class:`OracleRecord`:

- **inline pure-Python oracles** — run post-``apply`` with no extra generation (``Scenario.annotate_turn``),
  scoring the seat's ACTUAL move against the oracle's best on the same state. Cheap, so every turn can carry
  one.
- **forked provisional elicitations** — re-ask the *model* to finalize now on a private forked view
  (``Scenario.provisional_due``), an LLM-side probe of where the model thinks it stands.

Both land in ``Episode.round_checkpoints`` (kept as the field name for record compatibility) as
``OracleRecord.to_json()`` dicts.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Sequence

import numpy as np

from .actions import Action, action_from_json, action_from_key, action_key


def _jsonify(value: Any) -> Any:
	"""Recursively coerce an oracle's free-form ``beliefs`` / ``extra`` payload to JSON-safe data, so the
	episode's oracle log stays ``json.dumps``-able no matter what an oracle stashes there. THE single coercion for
	the negotiation oracle stack — ``oracle_context.make_verdict`` imports it too, so the ``|D|×n`` numpy tables
	and typed actions the oracles produce are serialized one way.

	numpy array/scalar → list/py-scalar; a dataclass (e.g. OpponentType) → its fields; an ``Action`` → its
	``to_json()``; a dict KEYED BY actions → the same ``[{"action", "value"}]`` list as ``action_values`` (a JSON
	object key can't be an object — the case that crashed a best-response oracle's action-keyed table); any other
	non-string dict key is stringified; lists/tuples recurse; primitives pass through."""
	if isinstance(value, np.ndarray):
		return value.tolist()
	if isinstance(value, np.generic):
		return value.item()
	to_json = getattr(value, "to_json", None)   # typed actions + any to_json-carrying object (e.g. OpponentType)
	if callable(to_json):
		try:
			return to_json()
		except Exception:
			pass
	if is_dataclass(value) and not isinstance(value, type):
		return _jsonify(asdict(value))
	if isinstance(value, dict):
		if value and all(isinstance(k, Action) for k in value):
			return [{"action": k.to_json(), "value": _jsonify(v)} for k, v in value.items()]
		return {(k if isinstance(k, str) else str(k)): _jsonify(v) for k, v in value.items()}
	if isinstance(value, (list, tuple)):
		return [_jsonify(v) for v in value]
	return value


@dataclass
class OracleVerdict:
	"""One oracle's read of a decision point.

	``action_values`` maps each evaluated action to its value (surplus / continuation value — the oracle's own
	units); ``best`` is the argmax action; ``beliefs`` optionally carries the oracle's posterior (e.g. a
	belief oracle's type distribution); ``flags`` are named hard-violation markers (e.g. ``"ir_violation"``,
	``"below_threshold_accept"``). ``extra`` is a free-form JSON-serializable dict for per-verdict diagnostics
	beyond the value table — e.g. a best-response oracle's per-action ``surplus_loss`` and ``best_response_deal``,
	an acceptance oracle's ``reservation`` / ``rounds_left``, an equilibrium oracle's ``v*`` — carried through
	``to_json`` into the episode's oracle log so the divergence atlas can read them. Actions are the dict keys,
	so they must be hashable — the formal :class:`~interlens.arena.actions.Action` dataclasses are frozen and
	satisfy this."""

	action_values: dict[Any, float]
	best: Any
	beliefs: dict | None = None
	flags: list[str] = field(default_factory=list)
	extra: dict = field(default_factory=dict)

	def value_of(self, action: Any) -> float | None:
		"""The value the oracle assigns ``action``, or ``None`` if it wasn't evaluated."""
		return self.action_values.get(action)

	def best_value(self) -> float | None:
		"""The value of the best action (``action_values[best]`` if present, else the max value, else ``None``)."""
		if self.best in self.action_values:
			return self.action_values[self.best]
		return max(self.action_values.values()) if self.action_values else None

	def divergence(self, action: Any) -> float | None:
		"""Regret of ``action``: ``best_value - value(action)`` (>= 0), or ``None`` if either is unknown."""
		best = self.best_value()
		chosen = self.value_of(action)
		if best is None or chosen is None:
			return None
		return best - chosen

	def to_json(self) -> dict:
		"""The stored form. ``action_values`` is a JSON OBJECT keyed by
		:func:`~interlens.arena.actions.action_key` (the action's ``to_json`` dumped with sorted keys) — a map,
		because that is what it is, so a reader can look one action's value up directly instead of scanning a
		list of pairs. ``best`` is the same key string, so ``stored['action_values'][stored['best']]`` is the
		best value. ``beliefs``/``extra`` are free-form oracle payloads run through :func:`_jsonify`, so an
		action-keyed dict or a numpy table an oracle stashed can't leave the record un-serializable."""
		return {"action_values": {action_key(a): v for a, v in self.action_values.items()},
		        "best": action_key(self.best), "beliefs": _jsonify(self.beliefs), "flags": list(self.flags),
		        "extra": _jsonify(self.extra)}

	@staticmethod
	def from_json(d: dict) -> "OracleVerdict":
		"""Rebuild an ``OracleVerdict`` from :meth:`to_json`, reconstructing typed
		:class:`~interlens.arena.actions.Action` keys (and ``best``) so the regret math works on a verdict loaded
		from a stored episode. ``beliefs``/``flags``/``extra`` come back as the JSON that was stored — ``extra``
		is free-form diagnostics, so the coercion :func:`_jsonify` applies on the way out is deliberately not
		inverted on the way in.

		Reads BOTH stored shapes: the current ``{action_key: value}`` object (episode ``schema_version`` v1.1+)
		and the original ``[{"action": {...}, "value": v}, ...]`` list of pairs (v1.0), so episodes recorded
		before the shape change still load and replay."""
		stored = d.get("action_values") or {}
		if isinstance(stored, list):                       # v1.0 episodes: a list of {action, value} pairs
			action_values = {action_from_json(item["action"]): item["value"] for item in stored}
			best = d.get("best")
			best = action_from_json(best) if isinstance(best, dict) else None
		else:
			action_values = {action_from_key(k): v for k, v in stored.items()}
			best = action_from_key(d.get("best"))
		return OracleVerdict(action_values=action_values, best=best,
		                     beliefs=d.get("beliefs"), flags=list(d.get("flags", [])),
		                     extra=d.get("extra", {}))


class Oracle(ABC):
	"""A rational reference policy that scores a seat's options at a decision point.

	Subclasses implement :meth:`evaluate`. The arguments are deliberately generic so the ABC carries no
	negotiation specifics:

	- ``game`` — the game definition (the negotiation ``GameSpec``: deal space, score sheets, thresholds).
	- ``history`` — the sequence of prior turns/actions the oracle may condition on.
	- ``agent`` — the seat being evaluated (its private info defines its value function).
	- ``legal`` — the legal actions available to ``agent`` now (the keys the verdict scores).
	"""

	name: str = "oracle"

	@abstractmethod
	def evaluate(self, game: Any, history: Sequence, agent: str, legal: Sequence) -> OracleVerdict:
		"""Return an :class:`OracleVerdict` scoring ``legal`` for ``agent`` given ``game`` and ``history``."""


@dataclass
class OracleRecord:
	"""One per-turn oracle annotation on an episode (the typed replacement for the loose checkpoint dict).

	Two provenances share this record and are distinguished by whether ``verdict`` is set:

	- **inline annotation** (``verdict`` present): an :class:`Oracle` scored the seat's ACTUAL move against its
	  best on the same state — ``divergence`` = ``best_value - chosen_value`` in the oracle's value units.
	- **forked provisional probe** (``verdict`` absent): the model was re-asked to finalize now on a private
	  forked view; ``provisional_action`` / ``score`` / ``content`` capture that probe (the legacy checkpoint
	  shape).
	"""

	round: int
	seat: str
	turn_idx: int = -1
	oracle: str | None = None
	# inline oracle annotation
	chosen_value: float | None = None
	best_value: float | None = None
	divergence: float | None = None
	verdict: dict | None = None
	flags: list[str] = field(default_factory=list)
	# forked provisional probe (LLM-side)
	provisional_action: Any = None
	score: float | None = None
	content: str | None = None

	@classmethod
	def annotation(cls, verdict: OracleVerdict, *, round: int, seat: str, oracle: str,
	               chosen_action: Any = None, turn_idx: int = -1) -> "OracleRecord":
		"""An inline-oracle record: the seat's ``chosen_action`` scored against ``verdict.best``."""
		chosen = verdict.value_of(chosen_action) if chosen_action is not None else None
		best = verdict.best_value()
		div = (best - chosen) if (best is not None and chosen is not None) else None
		return cls(round=round, seat=seat, turn_idx=turn_idx, oracle=oracle,
		           chosen_value=chosen, best_value=best, divergence=div,
		           verdict=verdict.to_json(), flags=list(verdict.flags))

	@classmethod
	def provisional(cls, *, round: int, seat: str, provisional_action: Any, score: float | None,
	                content: str | None, turn_idx: int = -1) -> "OracleRecord":
		"""A forked provisional-probe record (the ``Scenario.provisional_due`` path)."""
		return cls(round=round, seat=seat, turn_idx=turn_idx,
		           provisional_action=provisional_action, score=score, content=content)

	def to_json(self) -> dict:
		if self.verdict is not None:                       # inline oracle annotation
			out: dict = {"round": self.round, "seat": self.seat, "oracle": self.oracle,
			             "chosen_value": self.chosen_value, "best_value": self.best_value,
			             "divergence": self.divergence, "verdict": self.verdict}
			if self.turn_idx >= 0:
				out["turn_idx"] = self.turn_idx
			if self.flags:
				out["flags"] = list(self.flags)
			return out
		# forked provisional probe — the legacy checkpoint shape, unchanged for record compatibility
		return {"round": self.round, "seat": self.seat, "provisional_action": self.provisional_action,
		        "score": self.score, "content": self.content}


def annotate(oracles: Sequence[Oracle], game: Any, history: Sequence, agent: str, legal: Sequence,
             *, chosen_action: Any = None, round: int, seat: str, turn_idx: int = -1) -> list[OracleRecord]:
	"""Run every oracle over one decision point and return one inline :class:`OracleRecord` each — the ready
	helper a scenario calls from ``annotate_turn`` so its oracle wiring is a single line. Skips an oracle that
	raises (a broken oracle must not abort an episode)."""
	records: list[OracleRecord] = []
	for oracle in oracles:
		try:
			verdict = oracle.evaluate(game, history, agent, legal)
		except Exception:
			continue
		records.append(OracleRecord.annotation(verdict, round=round, seat=seat, oracle=oracle.name,
		                                        chosen_action=chosen_action, turn_idx=turn_idx))
	return records
