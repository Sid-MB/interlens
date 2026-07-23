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

"""The oracle layer: the verdict/regret math, the typed ``OracleRecord`` (both provenances), the ``annotate``
helper, and the engine plumbing that runs a scenario's inline oracles post-``apply`` into ``round_checkpoints``
(alongside the existing forked-provisional path, which now serializes through the same typed record)."""
from __future__ import annotations

import asyncio

from interlens.message import Message
from interlens.participant import Participant
from interlens.arena import EpisodePool, EpisodeStore
from interlens.arena.actions import Accept, Walk
from interlens.arena.oracles import Oracle, OracleRecord, OracleVerdict, annotate
from interlens.arena.scenario import Scenario
from interlens.arena.schema import Instance, SeatRequest, new_id


# ------------------------------------------------------------- verdict math ---

def test_verdict_values_best_and_divergence():
	v = OracleVerdict(action_values={Walk(): 1.0, Accept("O1"): 0.4}, best=Walk(), flags=["ir_ok"])
	assert v.value_of(Walk()) == 1.0
	assert v.best_value() == 1.0
	assert v.divergence(Accept("O1")) == 0.6      # regret = best - chosen
	assert v.divergence(Walk()) == 0.0
	# best_value falls back to the max when `best` isn't a scored key
	assert OracleVerdict(action_values={Walk(): 2.0}, best="unscored").best_value() == 2.0
	assert v.divergence("never-evaluated") is None


def test_verdict_to_json_serializes_action_keys():
	v = OracleVerdict(action_values={Accept("O1"): 0.5}, best=Accept("O1"), beliefs={"p": 0.7}, flags=["f"])
	j = v.to_json()
	assert j["action_values"] == [{"action": {"action": "accept", "offer_id": "O1"}, "value": 0.5}]
	assert j["best"] == {"action": "accept", "offer_id": "O1"} and j["beliefs"] == {"p": 0.7}


def test_verdict_extra_with_action_keys_is_json_serializable():
	"""Regression: a best-response oracle keys extra['surplus_loss'] by Action objects; to_json must still
	produce a json.dumps-able (and dataclasses.asdict-safe) record — Action objects can't be JSON keys."""
	import json
	from interlens.arena.actions import Propose
	v = OracleVerdict(action_values={Accept("O1"): 0.5, Walk(): 0.0}, best=Accept("O1"),
	                  beliefs={"types": {("weight",): 0.5}},   # non-str keys in beliefs too
	                  extra={"surplus_loss": {Accept("O1"): 0.0, Walk(): 0.5}, "best_deal": Propose(deal=(0, 1)),
	                         "note": "ok"})
	j = v.to_json()
	json.dumps(j)                                              # crashed before the fix (Action objects as keys)
	# an action-keyed sub-dict becomes the [{action, value}] list form, like action_values
	sl = j["extra"]["surplus_loss"]
	assert isinstance(sl, list)
	assert {"action": {"action": "accept", "offer_id": "O1"}, "value": 0.0} in sl
	assert j["extra"]["best_deal"] == {"action": "propose", "deal": [0, 1]}   # Action value -> its to_json
	assert j["extra"]["note"] == "ok"
	# the record that actually lands in round_checkpoints must also serialize
	rec = OracleRecord.annotation(v, round=1, seat="Avery", oracle="bestresponse", chosen_action=Walk())
	json.dumps(rec.to_json())
	# round-trip: from_json inverts the action-keyed surplus_loss back to an Action-keyed dict
	back = OracleVerdict.from_json(j)
	assert back.extra["surplus_loss"] == {Accept("O1"): 0.0, Walk(): 0.5}
	assert back.extra["best_deal"] == Propose(deal=(0, 1)) and back.extra["note"] == "ok"


def test_extra_preserialized_action_list_passes_through():
	"""oracles-strategies emits surplus_loss as an explicit already-serialized list
	[{"action": a.to_json(), "loss": v}] (and compacts belief extra to a summary). The sanitizer must leave
	that shape json-safe and INTACT (no double-wrapping), and one round-trip must be idempotent on it."""
	import json
	v = OracleVerdict(action_values={Accept("O1"): 0.5}, best=Accept("O1"),
	                  extra={"surplus_loss": [{"action": Accept("O1").to_json(), "loss": 1.5},
	                                          {"action": Walk().to_json(), "loss": 0.0}],
	                         "n_opponents": 5})
	j = v.to_json()
	json.dumps(j)
	assert j["extra"]["surplus_loss"] == [{"action": {"action": "accept", "offer_id": "O1"}, "loss": 1.5},
	                                      {"action": {"action": "walk"}, "loss": 0.0}]
	assert j["extra"]["n_opponents"] == 5
	assert OracleVerdict.from_json(j).to_json()["extra"] == j["extra"]   # round-trip idempotent on their shape


def test_verdict_json_round_trip_including_extra():
	from interlens.arena.actions import Propose
	v = OracleVerdict(action_values={Propose(deal=(0, 1)): 2.0, Accept("O1"): 0.5, Walk(): 0.0},
	                  best=Propose(deal=(0, 1)), beliefs={"types": [0.2, 0.8]}, flags=["ir_ok"],
	                  extra={"surplus_loss": {"O1": 1.5}, "best_response_deal": [0, 1], "v_star": 0.42})
	back = OracleVerdict.from_json(v.to_json())
	assert back.action_values == v.action_values          # action keys reconstructed as typed objects
	assert back.best == Propose(deal=(0, 1))
	assert back.beliefs == {"types": [0.2, 0.8]} and back.flags == ["ir_ok"]
	assert back.extra == {"surplus_loss": {"O1": 1.5}, "best_response_deal": [0, 1], "v_star": 0.42}
	assert back.divergence(Accept("O1")) == 1.5           # regret math survives the round-trip


# ----------------------------------------------------------------- records ---

def test_provisional_record_is_legacy_shape():
	rec = OracleRecord.provisional(round=2, seat="Avery", provisional_action={"answer": 5}, score=1.0,
	                               content="text")
	# byte-compatible with the pre-existing checkpoint dict (nothing else, so old datasets/readers are unaffected)
	assert rec.to_json() == {"round": 2, "seat": "Avery", "provisional_action": {"answer": 5},
	                         "score": 1.0, "content": "text"}


def test_annotation_record_carries_regret():
	v = OracleVerdict(action_values={Walk(): 1.0, Accept("O1"): 0.4}, best=Walk(), flags=["hot"])
	rec = OracleRecord.annotation(v, round=1, seat="Avery", oracle="solution",
	                              chosen_action=Accept("O1"), turn_idx=3)
	j = rec.to_json()
	assert j["oracle"] == "solution" and j["divergence"] == 0.6 and j["turn_idx"] == 3
	assert j["chosen_value"] == 0.4 and j["best_value"] == 1.0 and j["flags"] == ["hot"]
	assert "verdict" in j and "provisional_action" not in j


# ------------------------------------------------------------- annotate() ---

class _Const(Oracle):
	name = "const"

	def evaluate(self, game, history, agent, legal):
		return OracleVerdict(action_values={Walk(): 1.0, Accept("O1"): 0.0}, best=Walk(), flags=["x"])


class _Boom(Oracle):
	name = "boom"

	def evaluate(self, game, history, agent, legal):
		raise RuntimeError("a broken oracle must not abort the episode")


def test_annotate_runs_oracles_and_skips_failures():
	records = annotate([_Const(), _Boom()], game=None, history=[], agent="Avery",
	                   legal=[Walk(), Accept("O1")], chosen_action=Accept("O1"), round=1, seat="Avery")
	assert len(records) == 1                       # _Boom skipped, not fatal
	assert records[0].oracle == "const" and records[0].divergence == 1.0


# ----------------------------------------------------- engine plumbing (A2) ---

class _OneTurn(Scenario):
	"""A minimal 1-seat, 1-turn scenario that annotates its single turn with an inline oracle — exercises the
	engine's post-apply annotate path end to end."""

	name = "mini_oracle"

	def generate_instance(self, level, seed):
		return Instance(new_id("mini"), self.name, level, seed, {}, 1.0, 0.0, {})

	def make_state(self, instance, arm, seed, cfg=None):
		return {"inst": instance, "arm": arm, "events": [], "round": 1, "done": False}

	def seat_specs(self, state):
		return [{"name": "Avery", "role": "solo"}]

	def next_requests(self, state):
		if state["done"]:
			return []
		return [SeatRequest("", "Avery", [{"role": "user", "content": "go"}], "turn", 1, meta={})]

	def apply(self, state, request, text):
		state["_last_parse"] = (text, True)
		state["events"].append({"seat": request.seat, "content": text})
		state["done"] = True
		return None

	def score(self, state):
		return {"primary": 1.0, "success": True}

	def annotate_turn(self, state, request, turn):
		return annotate([_Const()], game=None, history=state["events"], agent=turn.seat,
		                legal=[Walk(), Accept("O1")], chosen_action=Accept("O1"),
		                round=turn.round, seat=turn.seat, turn_idx=turn.idx)


class _Speaker(Participant):
	name = "speaker"

	def generate(self, view, *, max_new_tokens=None, **kwargs):
		return Message(self.name, "I choose to accept.", {"n_tokens": 3, "n_tokens_in": 2})


def test_inline_oracle_annotation_flows_into_checkpoints(tmp_path):
	scen = _OneTurn()
	inst = scen.generate_instance(0, 1)
	ep = asyncio.run(EpisodePool(EpisodeStore(tmp_path)).run_episode(scen, inst, "team", _Speaker()))
	assert ep.status == "done"
	assert len(ep.round_checkpoints) == 1
	rec = ep.round_checkpoints[0]
	assert rec["oracle"] == "const" and rec["divergence"] == 1.0    # chose Accept (0.0) vs Walk best (1.0)
	assert rec["turn_idx"] == 0 and "verdict" in rec


class _InterpProbe(Participant):
	"""Records the interp kwargs each generation is called with (A3: capture/steering/patch/turn plumbing)."""

	name = "probe"

	def __init__(self):
		self.calls = []

	def generate(self, view, *, max_new_tokens=None, steering=None, capture=None, patch=None, turn=None,
	             **kwargs):
		self.calls.append({"steering": steering, "capture": capture, "patch": patch, "turn": turn})
		return Message(self.name, "ok", {"n_tokens": 1, "n_tokens_in": 1})


def test_run_episode_threads_interp_hooks_and_turn_index(tmp_path):
	scen = _OneTurn()
	inst = scen.generate_instance(0, 2)
	probe = _InterpProbe()
	cap_obj, steer_obj, patch_obj = object(), object(), object()
	asyncio.run(EpisodePool(EpisodeStore(tmp_path)).run_episode(
		scen, inst, "team", probe, capture=cap_obj, steering=steer_obj, patch=patch_obj))
	assert probe.calls == [{"steering": steer_obj, "capture": cap_obj, "patch": patch_obj, "turn": 0}]


def test_run_episode_without_interp_passes_nothing(tmp_path):
	scen = _OneTurn()
	inst = scen.generate_instance(0, 3)
	probe = _InterpProbe()
	asyncio.run(EpisodePool(EpisodeStore(tmp_path)).run_episode(scen, inst, "team", probe))
	# default run: no capture/steer/patch threaded (byte-identical to the pre-A3 call), turn omitted
	assert probe.calls == [{"steering": None, "capture": None, "patch": None, "turn": None}]
