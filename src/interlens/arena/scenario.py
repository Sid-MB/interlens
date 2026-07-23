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
	default_communication: str = "messaging"
	"""The communication mode task runners (e.g. the Inspect tasks) use when none is given. The package
	default is the async messaging system (``send_message``/``read_message`` mailboxes with pings and the
	priority scheduler — see ``interlens.communication.MessagingPolicy``); the round-robin published protocol
	and direct piping remain available as explicit configs (``communication="round_robin"``, or a
	``DirectPipingPolicy`` on a raw ``Conversation``). Scenarios with no sound messaging reduction override
	this (the security dilemma pins ``"round_robin"``). Note the shipped v0 transcript dataset was produced
	under the round-robin protocol (recorded per episode in ``gen_config``), so use ``round_robin`` when
	comparing against those cells."""

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

	def annotate_turn(self, state: dict, request: SeatRequest, turn) -> list:
		"""Inline per-turn oracle annotations, run by the engine right after ``apply`` commits ``turn`` (no extra
		generation). Return a list of ``interlens.arena.oracles.OracleRecord`` — the engine appends them to the
		episode's oracle log. A scenario with a pure-Python oracle stack scores the seat's ACTUAL move against
		the oracle's best here (``interlens.arena.oracles.annotate`` is the ready one-liner); the default runs no
		oracles. This is the inline sibling of the forked ``provisional_due`` path — the two coexist."""
		return []

	# ------------------------------------------------------------ messaging --
	def score_from_messaging(self, instance, transcript: list[tuple[str, str]],
	                         cfg: dict | None = None) -> dict | None:
		"""Score a free-form messaging-mode episode (the Inspect adapter's ``communication="messaging"``):
		``transcript`` is ``[(seat, text), ...]`` in send order. Return the outcome dict, or ``None`` when the
		scenario has no messaging reduction — the adapter then falls back to the final-answer/proposal
		reduction for scenarios whose protocol ends in one structured action, and raises otherwise."""
		return None

	def messaging_finalizable(self) -> bool:
		"""Whether a free-form messaging episode can be reduced to one final action by the adapter's
		final-answer/proposal extraction — True exactly when the protocol ends in a single structured answer that
		the deciding seat emits. Scenarios that instead implement ``score_from_messaging`` don't need this. The
		Inspect messaging adapter uses this capability (not a hardcoded scenario name) to decide whether it can
		run the scenario at all. Default: False."""
		return False

	def messaging_decider(self, state: dict) -> str:
		"""The seat whose last fenced action decides a messaging episode (the finalizer / proposer). The adapter
		scans this seat's turns for the deciding ``answer`` / ``proposal`` JSON. Default: the first seat."""
		return self.seat_specs(state)[0]["name"]

	# ---------------------------------------------------------- retry helper --
	def final_retry_directive(self, state: dict, request: SeatRequest, retry_prompt: str,
	                          *, key=None) -> dict | None:
		"""The one-retry-then-give-up bookkeeping shared by every scenario's forced-finalization phase: on the
		FIRST malformed final action for ``key`` (default ``("retry", request.round)``) return ``{'retry':
		retry_prompt}`` (the engine re-prompts once); on the second, return ``None`` so the caller finalizes with
		what it has. Idempotent per key via ``state['_r']``, so replay re-emits the identical retry."""
		key = key if key is not None else ("retry", request.round)
		seen = state.setdefault("_r", set())
		if key not in seen:
			seen.add(key)
			return {"retry": retry_prompt}
		return None

	# ------------------------------------------------------- solo-arm scaffold --
	# The one-mind-with-all-the-facts baseline shares an identical loop across scenarios: seed a full-info task,
	# let the seat iterate, finalize on a fenced answer, and — when the engine's budget fires
	# (``budget_exhausted``) or a hard iteration ceiling hits — force one last answer. Subclasses supply the
	# scenario-specific prompts and the parse/finalize hooks below; ``solo_requests`` / ``solo_apply`` drive the
	# common flow (the bundled negotiation / relay / long-context scenarios delegate to them).
	SOLO_SEAT: str = "Reader"
	SOLO_CEILING: int | None = None     # hard iteration cap for solo arms (None = only the engine budget stops it)

	def solo_system(self, state: dict) -> str:
		"""The solo seat's system prompt (full-info framing)."""
		raise NotImplementedError

	def solo_task(self, state: dict) -> str:
		"""The initial user task text seeding the solo conversation (all private info + the question)."""
		raise NotImplementedError

	def solo_continue(self, state: dict) -> str:
		"""The 'keep going, answer when ready' user nudge appended after a non-final solo turn."""
		raise NotImplementedError

	def solo_final_prompt(self, state: dict) -> str:
		"""The 'budget reached — answer NOW' user prompt for the forced-final solo turn."""
		raise NotImplementedError

	def solo_parse(self, state: dict, text: str) -> tuple:
		"""Parse one solo turn -> ``(parsed, parse_ok, has_final, answer)``: ``parsed`` is the extracted JSON,
		``parse_ok`` the value logged as the turn's ``parse_ok``, ``has_final`` whether the turn committed a final
		answer, and ``answer`` the finalized value passed to ``solo_finalize`` (may itself be ``None``)."""
		raise NotImplementedError

	def solo_finalize(self, state: dict, answer, text: str) -> None:
		"""Commit ``answer`` (from a genuine final turn) to state. The base sets ``done`` afterwards."""
		raise NotImplementedError

	def solo_give_up(self, state: dict) -> None:
		"""Commit a no-answer outcome when the forced-final turn produced no valid answer. Base sets ``done``."""
		raise NotImplementedError

	def solo_work_cap(self, state: dict) -> int:
		"""Per-turn output cap for a solo working turn. Default: ``solo_turn_cap`` cell knob, else 900."""
		return state.get("solo_turn_cap", 900)

	def solo_final_cap(self, state: dict) -> int:
		"""Per-turn output cap for the forced-final solo turn. Default: 2048."""
		return 2048

	def solo_requests(self, state: dict) -> list[SeatRequest]:
		"""The solo arm's ``next_requests``: forced-final on budget exhaustion (once), else seed the task on the
		first call and emit a working turn."""
		if state.get("budget_exhausted") and not state["done"]:
			if state.get("_forced_final"):
				state["done"] = True
				return []
			state["_forced_final"] = True
			view = ([{"role": "system", "content": self.solo_system(state)}]
			        + state["solo_msgs"]
			        + [{"role": "user", "content": self.solo_final_prompt(state)}])
			return [SeatRequest("", self.SOLO_SEAT, view, "solo_final", state["round"],
			                    max_tokens=self.solo_final_cap(state), meta={})]
		if not state["solo_msgs"]:
			state["solo_msgs"] = [{"role": "user", "content": self.solo_task(state)}]
		view = [{"role": "system", "content": self.solo_system(state)}] + state["solo_msgs"]
		return [SeatRequest("", self.SOLO_SEAT, view, "solo_work", state["round"],
		                    max_tokens=self.solo_work_cap(state), meta={})]

	def solo_apply(self, state: dict, request: SeatRequest, text: str) -> dict | None:
		"""The solo arm's ``apply``: record the turn, finalize on a genuine answer, give up on a forced-final that
		produced none, else (below any ``SOLO_CEILING``) nudge and continue."""
		parsed, parse_ok, has_final, answer = self.solo_parse(state, text)
		state["_last_parse"] = (parsed, parse_ok)
		state["solo_msgs"].append({"role": "assistant", "content": text})
		if has_final:
			self.solo_finalize(state, answer, text)
			state["done"] = True
			return None
		if request.phase == "solo_final":
			self.solo_give_up(state)
			state["done"] = True
			return None
		if self.SOLO_CEILING is not None and state["round"] >= self.SOLO_CEILING:
			state["budget_exhausted"] = True
			return None
		state["solo_msgs"].append({"role": "user", "content": self.solo_continue(state)})
		state["round"] += 1
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
