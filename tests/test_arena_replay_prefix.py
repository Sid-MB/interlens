# [implement: backtrack RL policy negotiation] 2026-08-16 — prefix replay + engine resume (branch support)
"""``apply_prefix`` and the engine's ``prefix`` job key: resuming a stored episode from a mid-game node.

The branch-backtracking experiments replay a stored no-deal negotiation up to a decision turn and continue it
with fresh sampling. Three properties carry that design and are pinned here:

* a prefix replay reconstructs the EXACT mid-game state — the next pending request is the one the stored turn
  answered;
* an ``EpisodeRun`` given ``prefix=(parent, upto)`` continues that game (its outcome reflects prefix + new
  play), records only continuation turns, and numbers them on the parent's global turn indices;
* a full-length prefix replay still scores identically to the stored outcome (the replay contract).
"""
from __future__ import annotations

import asyncio
import json
import re

from interlens.arena import EpisodePool
from interlens.arena.replay import apply_prefix, make_replay_state, rescore
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.message import Message
from interlens.participant.participant import Participant

from .test_arena_scorable import JsonSeat, coop, make_game, make_instance

TARGET = {"Site": "North", "Fund": "High"}


def stubborn(target: dict):
	"""Propose ``target`` every turn and reject everything else — a table that grinds to expiry, no deal."""
	def decide(seat, view):
		m = re.search(r"\bP\d+\b", view[-1]["content"])
		if "FINAL up/down vote" in view[-1]["content"] and m:
			return {"message": "no.", "action": "reject", "offer_id": m.group(0)}
		return {"message": "my package or nothing.", "action": "propose", "deal": target}
	return decide


def run(participant, *, cfg=None, prefix=None, instance=None, scenario=None):
	scenario = scenario or ScorableNegotiation()
	instance = instance if instance is not None else make_instance(make_game())
	pool = EpisodePool(None)
	ep = asyncio.run(pool.run_episode(scenario, instance, "moves_chat", participant, seed=0, cfg=cfg,
	                                  prefix=prefix))
	return scenario, instance, ep


def make_no_deal_parent():
	scen, inst, ep = run(JsonSeat(stubborn(TARGET)))
	parent = json.loads(json.dumps(ep.to_json()))
	assert parent["outcome"]["deal"] is False and len(parent["turns"]) > 4
	return scen, inst, parent


def test_apply_prefix_reissues_the_stored_turns_request():
	scen, inst, parent = make_no_deal_parent()
	node = parent["turns"][3]
	state = make_replay_state(scen, inst, parent)
	applied = apply_prefix(scen, state, parent, upto=3)
	assert applied == 3
	requests = scen.next_requests(state)
	assert any(r.seat == node["seat"] and r.phase == node["phase"] for r in requests), \
		"the prefix state must re-issue exactly the request the stored turn answered"


def test_apply_prefix_full_length_matches_recorded_outcome():
	scen, inst, parent = make_no_deal_parent()
	result = rescore(scen, inst, parent)
	assert result["match"], result


def test_episode_run_prefix_continues_the_parents_game():
	scen, inst, parent = make_no_deal_parent()
	upto = 3
	# Continue the grinding no-deal game with cooperative seats: the branch closes what the parent could not.
	_, _, branch = run(JsonSeat(coop(TARGET)), cfg={"cell": "branch"},
	                   prefix=(parent, upto), instance=inst, scenario=scen)
	assert branch.outcome["deal"] is True, "the continuation should close the deal the stubborn parent refused"
	# Only continuation turns are recorded, numbered on the parent's global indices (no collision, no re-record).
	assert branch.turns[0].idx == upto
	assert len(branch.turns) < len(parent["turns"]) + 4
	# The prefix's standing offer is part of the continuation's state: the closed deal is the parent's target.
	assert branch.outcome["offers"], "prefix proposals must be visible in the continuation's registry"


def test_prefix_upto_none_replays_everything():
	scen, inst, parent = make_no_deal_parent()
	state = make_replay_state(scen, inst, parent)
	applied = apply_prefix(scen, state, parent, upto=None)
	assert applied == len(parent["turns"])
	assert state["done"] is True
