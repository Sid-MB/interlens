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

"""Distributed long-context scenario: shard-partition property, exact graders on hand-checked fixtures,
truncation/capitulation outcome classes, directed-messaging privacy, and scripted end-to-end episodes."""
from __future__ import annotations

import asyncio
import random

from interlens.message import Message
from interlens.participant import Participant
from interlens.arena import EpisodePool, EpisodeStore, replay_episode
from interlens.arena.schema import Instance, new_id
from interlens.arena.scenarios import dlc_scenario
from interlens.arena.scenarios.dlc import (ADAPTERS, BCPAdapter, CodeQAAdapter, OolongPairsAdapter,
                                           SniahAdapter)
from interlens.arena.scenarios.dlc.build import (char_balanced_split, char_split4, char_split4_docs,
                                                 insert_needle)
from interlens.arena.scenarios.dlc.oolong_pairs import gold_pairs, parse_lines
from interlens.arena.scenarios.longcontext import N_ROUNDS, TURN_ORDER


# ------------------------------------------------------------------------------------------------ fixtures --

def _fixture_lines() -> list[str]:
	"""A hand-checked OOLONG-style window: 3 users with known label/date profiles."""
	return [
		"Date: Jan 10, 2023 || User: 101 || Instance: What is a barometer? || Label: entity",
		"Date: Feb 02, 2023 || User: 101 || Instance: Who was Ada Lovelace? || Label: human being",
		"Date: Mar 03, 2023 || User: 202 || Instance: How many meters in a mile? || Label: numeric value",
		"Date: Mar 04, 2023 || User: 202 || Instance: Where is Timbuktu? || Label: location",
		"Date: Apr 05, 2023 || User: 303 || Instance: What does NASA stand for? || Label: abbreviation",
	]


def _sniah_instance(n_paras: int = 40, seed: int = 7) -> Instance:
	rng = random.Random(seed)
	paras = [f"Paragraph {i}: " + " ".join(f"w{rng.randint(0, 99)}" for _ in range(30))
	         for i in range(n_paras)]
	hay = "\n\n".join(paras)
	needle = "One of the special magic numbers for juniper is: 4415926."
	full, _depth = insert_needle(rng, hay, needle)
	shards = char_split4(full)
	assert sum(s.count(needle) for s in shards) == 1
	return Instance(new_id("sniah-fix"), "dlc_sniah", 0, seed,
	                {"task": "sniah",
	                 "question": "What is the special magic number for juniper?",
	                 "shards": shards, "gold_number": "4415926"},
	                1.0, 0.0, {"number": "4415926"})


def _oolong_instance() -> Instance:
	lines = _fixture_lines()
	rows = parse_lines("\n".join(lines))
	# query 1 (index 0): both users have >= 1 numeric value or location instance -> only (202,) qualifies
	# with itself excluded, so gold is empty; query 2 (index 1): entity-or-human -> only user 101, no pair.
	# Use query index 11 semantics? Keep it simple: grade against programmatic gold for query 0.
	gold = sorted(gold_pairs(rows, 0))
	blocks = char_balanced_split(lines)
	shards = ["\n".join(b) + "\n" for b in blocks]
	return Instance(new_id("op-fix"), "dlc_oolong_pairs", 0, 1,
	                {"task": "oolong_pairs", "question": "List all pairs ...",
	                 "shards": shards, "gold_pairs": [list(p) for p in gold]},
	                1.0, 0.0, {"n_gold": len(gold)})


# ---------------------------------------------------------------------------------------- shard partition --

def test_partition_property_char_split4():
	rng = random.Random(0)
	for n in (37, 400, 5000):
		text = "\n".join("line " + "x" * rng.randint(0, 80) for _ in range(n))
		shards = char_split4(text)
		assert len(shards) == 4
		assert "".join(shards) == text          # no loss, no overlap, order preserved


def test_partition_property_char_balanced_split():
	lines = [f"Date: line {i} " + "y" * (i % 17) for i in range(200)]
	blocks = char_balanced_split(lines)
	flat = [ln for b in blocks for ln in b]
	assert flat == lines                        # exact line partition
	sizes = [sum(len(ln) + 1 for ln in b) for b in blocks]
	assert max(sizes) - min(sizes) < 2 * max(len(ln) + 1 for ln in lines)


def test_partition_property_char_split4_docs():
	docs = [f"### Document d{i}\nbody {'z' * (i * 7 % 91)}\n" for i in range(23)]
	shards = char_split4_docs(docs)
	assert "".join(shards) == "".join(docs)
	# documents are never split across shards
	for i in range(23):
		assert sum(s.count(f"### Document d{i}\n") for s in shards) == 1


# ------------------------------------------------------------------------------------------------ graders --

def test_sniah_grader_exact_match():
	a = SniahAdapter()
	payload = {"gold_number": "4415926"}
	assert a.parse_answer("", {"answer": "the number is 4415926"}) == "4415926"
	assert a.grade("4415926", payload) == {"primary": 1.0, "success": True, "gold": "4415926"}
	assert a.grade("4415927", payload)["primary"] == 0.0
	assert a.grade(None, payload)["success"] is False
	assert a.parse_answer("", {"answer": "no digits"}) is None


def test_oolong_gold_pairs_hand_checked():
	rows = parse_lines("\n".join(_fixture_lines()))
	assert len(rows) == 5 and len({r.user for r in rows}) == 3
	# query 0: both users have >=1 numeric-value-or-location instance. User profiles:
	# 101 {entity, human}, 202 {numeric, location}, 303 {abbreviation} -> no qualifying pair.
	assert gold_pairs(rows, 0) == set()
	# query 1: both users have >=1 entity-or-human-being instance -> only 101 qualifies -> no pair.
	assert gold_pairs(rows, 1) == set()


def test_oolong_grader_f1_hand_computed():
	a = OolongPairsAdapter()
	payload = {"gold_pairs": [[101, 202], [101, 303]]}
	# predicted {101,202} only: precision 1, recall 1/2, F1 = 2*(1*0.5)/1.5 = 2/3
	out = a.grade([(101, 202)], payload)
	assert abs(out["f1"] - 2 / 3) < 1e-12 and not out["success"]
	assert out["n_pred"] == 1 and out["n_gold"] == 2
	# exact set -> success
	assert a.grade([(101, 202), (101, 303)], payload)["success"]
	# empty gold and empty prediction -> perfect
	assert a.grade([], {"gold_pairs": []})["primary"] == 1.0
	# unordered + string forms normalize
	assert a.parse_answer("", {"answer": [[202, 101], "(101, 303)"]}) == [(101, 202), (101, 303)]


def test_codeqa_grader_choice_match():
	a = CodeQAAdapter()
	assert a.parse_answer("", {"answer": " b "}) == "B"
	assert a.grade("B", {"gold_choice": "B"})["success"]
	assert a.grade("A", {"gold_choice": "B"})["primary"] == 0.0


def test_bcp_grader_is_two_phase_unjudged():
	a = BCPAdapter()
	out = a.grade("Paris", {"gold_answer": "Paris"})
	assert out == {"primary": 0.0, "success": False, "judged": False, "gold": "Paris"}


def test_adapters_registry():
	assert sorted(ADAPTERS) == ["bcp", "codeqa", "oolong_pairs", "sniah"]


# ----------------------------------------------------------------------------------------- outcome classes --

def _turn(idx, stop_reason=None, content="", cap=100, tokens_out=10):
	return {"idx": idx, "round": 1, "phase": "turn", "seat": "Avery", "content": content,
	        "stop_reason": stop_reason, "cap": cap, "n_tokens_out": tokens_out}


def test_truncation_classification():
	scen = dlc_scenario("sniah")
	st = scen.make_state(_sniah_instance(), "team", 0)
	outcome = {"answered": True, "primary": 1.0}
	clean = scen.classify_outcome(st, [_turn(0), _turn(1)], outcome)
	assert clean["outcome_class"] == "answered" and not clean["truncated_at_budget"]
	trunc = scen.classify_outcome(st, [_turn(0), _turn(1, stop_reason="max_tokens")], outcome)
	assert trunc["outcome_class"] == "truncated_at_budget" and trunc["truncated_at_budget"]
	assert trunc["truncations"] == [{"turn_idx": 1, "phase": "turn", "seat": "Avery",
	                                 "round": 1, "cap": 100, "tokens_out": 10}]
	no_ans = scen.classify_outcome(st, [_turn(0)], {"answered": False})
	assert no_ans["outcome_class"] == "no_answer"


def test_capitulation_classification():
	scen = dlc_scenario("oolong_pairs")
	shards = ["Date: x || User: 1001 || Instance: q\nDate: x || User: 1002 || Instance: q\n",
	          "Date: x || User: 1003 || Instance: q\n", "filler", "filler"]
	inst = Instance(new_id("op-cap"), "dlc_oolong_pairs", 0, 1,
	                {"task": "oolong_pairs", "question": "q", "shards": shards,
	                 "gold_pairs": [[1001, 1002], [1001, 1003], [1002, 1003]]},
	                1.0, 0.0, {})
	st = scen.make_state(inst, "team", 0)
	# short answer (1 of 3 gold), NOT truncated, users discussed -> capitulated
	turns = [_turn(0, content="I hold users 1001 and 1002; 1003 is with Blake.")]
	out = scen.classify_outcome(st, turns, {"answered": True, "n_gold": 3, "n_pred": 1})
	assert out["outcome_class"] == "capitulated" and out["capitulated"]
	ev = out["capitulation_evidence"]
	assert ev["users_identified_in_discussion"] == 3 and ev["n_known_users"] == 3
	assert ev["pairs_emitted"] == 1 and ev["n_gold"] == 3
	# truncated episodes are NOT capitulation (they ran out of room)
	tr = scen.classify_outcome(st, [_turn(0, stop_reason="length")],
	                           {"answered": True, "n_gold": 3, "n_pred": 1})
	assert tr["outcome_class"] == "truncated_at_budget" and "capitulated" not in tr
	# a full answer is not capitulation
	ok = scen.classify_outcome(st, turns, {"answered": True, "n_gold": 3, "n_pred": 3})
	assert ok["outcome_class"] == "answered"


# ------------------------------------------------------------------------------------------- state machine --

class _SeatScript(Participant):
	"""Scripted 4-seat player: analysts share notes; the finalizer answers on its final-round turn."""

	def __init__(self, answer_json: str, msg_mode: bool = False):
		self.name = "scripted"
		self.answer_json = answer_json
		self.msg_mode = msg_mode

	def generate(self, view, *, max_new_tokens=None, **kwargs):
		last = view[-1]["content"]
		if "submit the team's answer" in last or "You MUST now submit" in last:
			text = self.answer_json
		elif self.msg_mode and '{"messages"' in last:
			text = '```json\n{"messages": [{"to": "all", "content": "notes from my shard"}]}\n```'
		else:
			text = "Sharing what my part says."
		return Message(self.name, text, {"n_tokens": 10, "n_tokens_in": 50})


def test_scripted_team_episode_round_robin(tmp_path):
	scen = dlc_scenario("sniah")
	inst = _sniah_instance()
	pool = EpisodePool(EpisodeStore(tmp_path))
	player = _SeatScript('```json\n{"answer": "4415926"}\n```')
	ep = asyncio.run(pool.run_episode(scen, inst, "team", player))
	assert ep.status == "done"
	assert ep.outcome["success"] and ep.outcome["answered"]
	assert ep.outcome["outcome_class"] == "answered"
	# turn order: finalizer (seat 0) last each round
	seats = [t.seat for t in ep.turns]
	names = [s["name"] for s in scen.seat_specs(scen.make_state(inst, "team", 0))]
	assert seats[:4] == [names[i] for i in TURN_ORDER]
	# replay reproduces the outcome, including the class
	rep = replay_episode(scen, inst, ep.to_json())
	assert rep["success"] == ep.outcome["success"]
	assert rep["outcome_class"] == ep.outcome["outcome_class"]


def test_scripted_team_msg_episode_routing_privacy(tmp_path):
	scen = dlc_scenario("sniah")
	inst = _sniah_instance()
	st = scen.make_state(inst, "team-msg", 0)
	names = st["seat_names"]
	# analyst 1 sends a private message to the finalizer only
	req = scen.next_requests(st)[0]
	assert req.seat == names[1]
	scen.apply(st, req, '```json\n{"messages": [{"to": "%s", "content": "SECRET-4415926"}]}\n```' % names[0])
	ev = st["events"][-1]
	assert ev["only"] == [names[0], names[1]]     # recipient + sender only
	# a broadcast goes public
	req = scen.next_requests(st)[0]
	scen.apply(st, req, '```json\n{"messages": [{"to": "all", "content": "public note"}]}\n```')
	assert "only" not in st["events"][-1]
	# malformed routing: one retry, then dropped
	req = scen.next_requests(st)[0]
	directive = scen.apply(st, req, "just chatting without JSON")
	assert directive and "retry" in directive


def test_scripted_solo_episode_with_iteration_ceiling(tmp_path):
	scen = dlc_scenario("sniah")
	inst = _sniah_instance()
	pool = EpisodePool(EpisodeStore(tmp_path))

	class NeverAnswers(Participant):
		name = "stuck"

		def generate(self, view, *, max_new_tokens=None, **kwargs):
			if "Token budget reached" in view[-1]["content"]:
				return Message(self.name, '```json\n{"answer": "4415926"}\n```', {"n_tokens": 5})
			return Message(self.name, "still thinking...", {"n_tokens": 5})

	ep = asyncio.run(pool.run_episode(scen, inst, "solo", NeverAnswers()))
	assert ep.status == "done"
	# the hard 8-iteration ceiling forces the budget path, whose forced-final answer succeeds
	assert ep.outcome["answered"] and ep.outcome["success"]
	assert any(t.phase == "solo_final" for t in ep.turns)


def test_generate_instance_raises():
	scen = dlc_scenario("codeqa")
	try:
		scen.generate_instance(0, 1)
		assert False, "expected RuntimeError"
	except RuntimeError as e:
		assert "offline" in str(e)


def test_oolong_fixture_scores_through_scenario():
	scen = dlc_scenario("oolong_pairs")
	inst = _oolong_instance()
	st = scen.make_state(inst, "team", 0)
	st["answer"] = []
	out = scen.score(st)
	assert out["primary"] == 1.0            # empty gold, empty prediction
	assert scen.rounds_used(st) == 1 and N_ROUNDS == 4
