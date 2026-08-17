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

"""Deterministic replay of stored episodes through a scenario's state machine.

An ``Episode`` record stores every committed turn's text. Because a ``Scenario`` is a pure state machine —
text in, state out, no RNG in stepping — feeding those turns back through ``apply`` reconstructs the exact
final state and re-derives the outcome with the *current* parser and scorer. Uses:

- **audit**: verify a stored dataset's recorded outcomes against the packaged scorer (the arena export's own
  reproduction check runs on exactly this);
- **re-scoring**: recompute outcomes under an extended scorer without re-running any model;
- **analysis**: reconstruct intermediate states (support maps, challenge ledgers) at any turn.

Replay is exact for episodes produced by this engine (and the arena experiments that share its schema): the
turn log stores think-stripped visible content in scenario order, provisional turns live separately in
``round_checkpoints`` (they never touched state), and the one-retry flow re-emits the same request, which is
how ``apply`` sees it here too.
"""
from __future__ import annotations

from .scenario import Scenario
from .schema import Instance

# outcome fields compared by default: the scoreboard identity of an episode
DEFAULT_FIELDS = ("success", "primary", "finalized_by")


class ReplayError(RuntimeError):
	"""A stored turn could not be matched to the state machine's pending request."""


def make_replay_state(scenario: Scenario, instance: Instance, episode: dict) -> dict:
	"""A fresh state built exactly the way ``episode`` was: same instance, arm, seed, and ``cell_cfg`` (minus
	the resolved personas, which ``make_state`` re-resolves identically from the seed)."""
	cfg = {k: v for k, v in (episode.get("cell_cfg") or {}).items() if k != "personas_resolved"}
	try:
		return scenario.make_state(instance, episode["arm"], episode["seed"], cfg=cfg or None)
	except TypeError:
		return scenario.make_state(instance, episode["arm"], episode["seed"])


def apply_prefix(scenario: Scenario, state: dict, episode: dict, upto: int | None = None, *,
                 on_turn=None) -> int:
	"""Replay ``episode``'s stored turns into an existing ``state``, stopping before turn index ``upto``.

	This is the branch/resume primitive: after it returns, ``state`` is exactly the mid-game state the engine
	held live just before the stored turn whose ``idx`` equals ``upto`` — ``next_requests(state)`` re-issues
	that turn's request, and play can continue with different text from there. ``upto=None`` replays every
	stored turn (the full-replay case). Matching is by the stored turn's ``idx`` field, not list position, so a
	record whose turns start above zero (itself a branch continuation) replays correctly.

	``on_turn`` is an optional ``callable(state, request, turn) -> None`` invoked after each turn is applied,
	while ``state`` still holds that turn's post-move context — the hook for post-hoc per-turn work (re-running
	oracles, reconstructing intermediate ledgers). Its return value is ignored; raising aborts the replay.

	Returns the number of turns applied. Raises :class:`ReplayError` if a stored turn cannot be matched to a
	pending request, or if ``upto`` is not reached because the record has fewer turns."""
	applied = 0
	for turn in episode["turns"]:
		if upto is not None and int(turn.get("idx", applied)) >= int(upto):
			return applied
		request = _match_request(scenario, state, turn)
		scenario.apply(state, request, turn["content"])
		applied += 1
		if on_turn is not None:
			on_turn(state, request, turn)
	if upto is not None and applied < int(upto):
		raise ReplayError(f"prefix asked for turns up to idx {upto} but the record holds only {applied}")
	return applied


def replay_episode(scenario: Scenario, instance: Instance, episode: dict, *, on_turn=None) -> dict:
	"""Feed a stored episode's turns back through ``scenario`` and return the recomputed outcome dict.

	``episode`` is the stored JSON record (``Episode.to_json()`` shape; the arena experiments' records load
	directly). The instance must be the one the episode was played on (``episode['instance_id']``).

	``on_turn`` is as in :func:`apply_prefix`, whose full-replay case this is."""
	state = make_replay_state(scenario, instance, episode)
	apply_prefix(scenario, state, episode, on_turn=on_turn)
	outcome = scenario.score(state)
	# the same post-scoring refinement the engine applies live (e.g. the distributed long-context
	# truncation/capitulation outcome classes) — pure in (state, turns, outcome), so it replays exactly
	outcome.update(scenario.classify_outcome(state, episode["turns"], outcome) or {})
	return outcome


def _match_request(scenario: Scenario, state: dict, turn: dict):
	"""The pending request corresponding to one stored turn. A stored forced-finalization turn (its phase says
	so, but a fresh state machine doesn't know the budget fired) re-requests with ``budget_exhausted`` set —
	the same signal the engine set live."""
	for _attempt in range(2):
		requests = scenario.next_requests(state)
		for request in requests:
			if request.seat == turn["seat"] and request.phase == turn["phase"]:
				return request
		# a budget-forced phase (e.g. solo_final) only appears once the exhaustion flag is set
		if not state.get("budget_exhausted"):
			state["budget_exhausted"] = True
			continue
		break
	raise ReplayError(
		f"stored turn (seat={turn['seat']!r}, phase={turn['phase']!r}, round={turn['round']}) has no matching "
		f"pending request — the episode was not produced by this scenario/state machine")


def rescore(scenario: Scenario, instance: Instance, episode: dict,
            fields: tuple[str, ...] = DEFAULT_FIELDS) -> dict:
	"""Replay ``episode`` and compare the recomputed outcome to the recorded one on ``fields``.

	Returns ``{"match": bool, "recorded": {...}, "recomputed": {...}, "mismatches": [field, ...]}``."""
	recomputed = replay_episode(scenario, instance, episode)
	recorded = episode.get("outcome") or {}
	mismatches = [f for f in fields
	              if f in recorded and recorded.get(f) != recomputed.get(f)]
	return {"match": not mismatches,
	        "recorded": {f: recorded.get(f) for f in fields},
	        "recomputed": {f: recomputed.get(f) for f in fields},
	        "mismatches": mismatches}
