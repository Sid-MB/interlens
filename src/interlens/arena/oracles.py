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
from dataclasses import dataclass, field
from typing import Any, Sequence

from .actions import Action, action_from_json


def _ser(action: Any) -> Any:
	"""JSON-safe rendering of an action key (an ``Action`` -> its ``to_json``, anything else unchanged)."""
	return action.to_json() if isinstance(action, Action) else action


def _de(value: Any) -> Any:
	"""Inverse of :func:`_ser`: rebuild an ``Action`` from a serialized action dict, else pass through."""
	if isinstance(value, dict) and any(k in value for k in ("action", "type", "kind")):
		try:
			return action_from_json(value)
		except ValueError:
			return value
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
		return {"action_values": [{"action": _ser(a), "value": v} for a, v in self.action_values.items()],
		        "best": _ser(self.best), "beliefs": self.beliefs, "flags": list(self.flags),
		        "extra": dict(self.extra)}

	@staticmethod
	def from_json(d: dict) -> "OracleVerdict":
		"""Rebuild an ``OracleVerdict`` from :meth:`to_json` — the round-trip inverse. Serialized action keys and
		``best`` are reconstructed into typed :class:`~interlens.arena.actions.Action` objects
		(via :func:`~interlens.arena.actions.action_from_json`); ``beliefs`` / ``flags`` / ``extra`` come back
		verbatim. Lets an analysis layer reconstruct typed verdicts (and their regret math) from stored
		episodes."""
		action_values = {_de(item["action"]): item["value"] for item in d.get("action_values", [])}
		return OracleVerdict(action_values=action_values, best=_de(d.get("best")),
		                     beliefs=d.get("beliefs"), flags=list(d.get("flags", [])),
		                     extra=dict(d.get("extra", {})))


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
