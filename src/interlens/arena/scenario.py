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

"""The ``Scenario`` interface: a pure game-logic state machine, participant-agnostic.

A scenario owns everything about the *game* — instance generation (with an exact solver for
ceilings/verification), per-seat private framing, the turn protocol, structured-action parsing, early
termination, and scoring — and nothing about *models*: it emits ``SeatRequest``s (who must speak now, on what
view) and consumes the resulting text. The engine (``engine.py``) owns persistence, retries, provisional
forking, budgets, and driving participants.

(The concept is a *scenario*, not an "environment": these are turn-based game protocols with exact scorers,
without RL/gym step/reward semantics.)

State is a plain dict owned by the scenario. Required keys maintained by every scenario:

- ``events``: ``list[{seat, content, only?}]`` — the public transcript (``MODERATOR`` for announcements;
  ``only`` restricts an event to named seats)
- ``round``: 1-based current round
- ``done``: bool
- ``arm``: ``"team"`` | ``"solo"`` | variant tags like ``"team-greedy"``

The engine sets ``state["budget_exhausted"] = True`` when an episode token/cost budget fires; scenarios must
then steer to a forced finalization (both bundled scenarios do).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .schema import Instance, SeatRequest


class Scenario(ABC):
	name: str = ""
	N_LEVELS: int = 5
	has_solo: bool = True

	# ---------------------------------------------------------- instances --
	@abstractmethod
	def generate_instance(self, level: int, seed: int) -> Instance:
		"""Generate one solver-verified instance at ``level`` from ``seed`` (deterministic payload per seed)."""

	# ------------------------------------------------------------- states --
	@abstractmethod
	def make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict:
		"""Fresh episode state. For ``arm='solo'`` the single seat gets ALL private info; solo episodes iterate
		until a final action or the engine's budget forces finalization. ``cfg`` is an optional sweep-cell
		config (situational knobs: rounds, framings, personas); scenarios that don't support one may ignore it."""

	@abstractmethod
	def seat_specs(self, state: dict) -> list[dict]:
		"""``[{name, role, ...}]`` for the episode record."""

	# ------------------------------------------------------------ stepping --
	@abstractmethod
	def next_requests(self, state: dict) -> list[SeatRequest]:
		"""The requests due now (>1 only for simultaneous phases). ``[]`` iff done. ``episode_id`` on the
		returned requests is filled by the engine."""

	@abstractmethod
	def apply(self, state: dict, request: SeatRequest, text: str) -> dict | None:
		"""Parse ``text``, mutate state (append events, record actions, advance phase/round, set ``done``).
		Return ``{'retry': <prompt>}`` to request ONE re-prompt of the same seat (engine-enforced), else
		``None``. Must record the parsed action for the turn log via
		``state['_last_parse'] = (parsed_action, parse_ok)``."""

	# ----------------------------------------------------------- provisional --
	def provisional_due(self, state: dict) -> list[SeatRequest]:
		"""Forked finalize-now elicitations due at this point (the engine calls right after each applied wave).
		Provisional responses never enter state or any transcript. Default: none."""
		return []

	def score_provisional(self, state: dict, parsed) -> float | None:
		"""Score a provisional final action with the normal scorer. Default: not scored."""
		return None

	# ------------------------------------------------------------ messaging --
	def score_from_messaging(self, instance, transcript: list[tuple[str, str]],
	                         cfg: dict | None = None) -> dict | None:
		"""Score a free-form messaging-mode episode (the Inspect adapter's ``communication="messaging"``):
		``transcript`` is ``[(seat, text), ...]`` in send order. Return the outcome dict, or ``None`` when the
		scenario has no messaging reduction — the adapter then falls back to the final-answer/proposal
		reduction for scenarios whose protocol ends in one structured action, and raises otherwise."""
		return None

	# -------------------------------------------------------------- scoring --
	def classify_outcome(self, state: dict, turns: list, outcome: dict) -> dict:
		"""Post-scoring outcome refinement, merged into the episode's outcome by the engine AND by replay.
		Must be pure in ``(state, turns, outcome)``. ``turns`` items are ``TurnRecord``s live and plain dicts in
		replay — read fields defensively. Default: no refinement. The distributed long-context scenario uses
		this for its ``truncated_at_budget`` / ``capitulated`` outcome classes."""
		return {}

	@abstractmethod
	def score(self, state: dict) -> dict:
		"""Final outcome dict. Must include ``primary`` (float, higher is better) and ``success`` (bool) where
		meaningful, plus scenario-specific fields."""

	def rounds_used(self, state: dict) -> int:
		return state.get("round", 0)

	def seat_framings(self, state: dict) -> dict:
		"""``{seat_name: verbatim system prompt}`` for a fresh state — the private framing each seat receives.
		Team arms render every seat directly; solo arms capture the single seat's system prompt from its first
		request. Lets a dataset/record ship self-contained framings."""
		out: dict = {}
		for r in self.next_requests(state):
			system = next((m["content"] for m in r.view if m["role"] == "system"), "")
			out[r.seat] = system
		fn = getattr(self, "system_prompt", None)
		if fn is not None and state.get("arm") != "solo":
			for si, spec in enumerate(self.seat_specs(state)):
				try:
					out.setdefault(spec["name"], fn(state, si))
				except Exception:
					pass
		return out
