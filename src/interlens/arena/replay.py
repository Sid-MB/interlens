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


def replay_episode(scenario: Scenario, instance: Instance, episode: dict) -> dict:
	"""Feed a stored episode's turns back through ``scenario`` and return the recomputed outcome dict.

	``episode`` is the stored JSON record (``Episode.to_json()`` shape; the arena experiments' records load
	directly). The instance must be the one the episode was played on (``episode['instance_id']``)."""
	cfg = {k: v for k, v in (episode.get("cell_cfg") or {}).items() if k != "personas_resolved"}
	try:
		state = scenario.make_state(instance, episode["arm"], episode["seed"], cfg=cfg or None)
	except TypeError:
		state = scenario.make_state(instance, episode["arm"], episode["seed"])
	for turn in episode["turns"]:
		request = _match_request(scenario, state, turn)
		scenario.apply(state, request, turn["content"])
	return scenario.score(state)


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
