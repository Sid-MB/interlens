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

"""Arena scenarios: generator↔solver agreement, hand-checked scoring, game flow, coherence, and the
situational knobs — ported from the arena experiments' offline suites (no models, no network)."""
from __future__ import annotations

import json

import pytest

from interlens.arena.scenarios import InfoRelay, Negotiation
from interlens.arena.scenarios.negotiation import (
	ISSUES, LEVEL_BUCKETS, _deal_scores, _enumerate_deals, _feasible, persona_assignment)
from interlens.arena.scenarios.priors import PRIORS, conflicted_slots, sheet_argmax_option
from interlens.arena.scenarios.relay import (
	FRAMINGS, HONEST_PERSONA, HOPS, N_DISTRACT, TOL, WRONG_PERSONA)


# --- negotiation ------------------------------------------------------------------------------------------

def test_negotiation_generator_hits_buckets_and_solution_is_exact():
	scen = Negotiation()
	for level in range(5):
		for seed in (1, 2):
			inst = scen.generate_instance(level, seed)
			p = inst.payload
			lo, hi = LEVEL_BUCKETS[level]
			assert lo <= p["feasible_count"] <= hi, (level, p["feasible_count"])
			# independent re-enumeration must agree with the stored solution
			deals = _enumerate_deals()
			feasible = [d for d in deals
			            if _feasible(d, p["sheets"], p["threshold"], p["proposer"], p["veto"])]
			assert len(feasible) == p["feasible_count"]
			best = max(feasible, key=lambda d: sum(_deal_scores(d, p["sheets"])))
			assert abs(sum(_deal_scores(best, p["sheets"])) - p["max_feasible_joint"]) < 1e-9
			named = {ISSUES[i][0]: ISSUES[i][1][best[i]] for i in range(5)}
			assert named == inst.solution["best_deal"]
			assert 0.0 < inst.floor <= 1.0


def test_negotiation_sweep_generator_scales_party_count():
	scen = Negotiation()
	for n_parties in (3, 4, 8):
		inst = scen.generate_instance_n(n_parties, seed=5)
		p = inst.payload
		assert p["n_parties"] == n_parties
		assert len(p["sheets"]) == n_parties
		assert p["deal_space"] == len(_enumerate_deals())  # issue set fixed across party counts
		feasible = [d for d in _enumerate_deals()
		            if _feasible(d, p["sheets"], p["threshold"], p["proposer"], p["veto"])]
		assert len(feasible) == p["feasible_count"]


def test_negotiation_scorer_hand_checked():
	scen = Negotiation()
	inst = scen.generate_instance(0, 42)
	st = scen.make_state(inst, "team", 0)
	p = inst.payload
	best = inst.solution["best_deal"]
	deal = scen._deal_from_json(st, best)
	assert deal is not None
	assert abs(scen._deal_primary(st, deal) - 1.0) < 1e-9
	# hand-check per-seat sums against a manual recomputation
	manual = []
	for si in range(6):
		total = 0.0
		for i, (issue_name, options) in enumerate(ISSUES):
			total += p["sheets"][si][i][options.index(best[issue_name])]
		manual.append(total)
	for a, b in zip(manual, _deal_scores(deal, p["sheets"])):
		assert abs(a - b) < 1e-9
	assert scen._deal_primary(st, None) == 0.0  # no deal scores 0


def test_negotiation_game_flow_consensus_and_forced_final():
	scen = Negotiation()
	inst = scen.generate_instance(0, 7)
	best = inst.solution["best_deal"]

	# seat 0 proposes the best deal; everyone supports it in round 1 -> consensus
	st = scen.make_state(inst, "team", 0)
	for turn in range(6):
		reqs = scen.next_requests(st)
		assert len(reqs) == 1
		text = ('I propose this. ```json\n{"proposal": ' + json.dumps(best) + "}\n```" if turn == 0
		        else 'Agreed. ```json\n{"support": "P1"}\n```')
		scen.apply(st, reqs[0], text)
	assert st["done"] and st["finalized_by"] == "consensus"
	out = scen.score(st)
	assert out["success"] and abs(out["primary"] - 1.0) < 1e-9
	assert out["support_final"]  # the negotiation ledger is recorded

	# no consensus -> forced final proposal path
	st2 = scen.make_state(inst, "team", 0)
	n = 0
	while not st2["done"]:
		req = scen.next_requests(st2)[0]
		if req.phase == "final_proposal":
			scen.apply(st2, req, '```json\n{"proposal": ' + json.dumps(best) + "}\n```")
		else:
			scen.apply(st2, req, "Let me think about our options here.")
		n += 1
		assert n < 40
	assert st2["finalized_by"] == "forced_final"
	assert scen.score(st2)["success"]


def test_negotiation_provisional_forked_and_scored():
	scen = Negotiation()
	inst = scen.generate_instance(0, 9)
	st = scen.make_state(inst, "team", 0)
	best = inst.solution["best_deal"]
	marks_seen = []
	while not st["done"]:
		req = scen.next_requests(st)[0]
		if req.phase == "final_proposal":
			scen.apply(st, req, '```json\n{"proposal": ' + json.dumps(best) + "}\n```")
		else:
			scen.apply(st, req, "Considering.")
			if scen.provisional_due(st):
				marks_seen.append(st["turn_count"])
				assert abs(scen.score_provisional(st, {"proposal": best}) - 1.0) < 1e-9
				# fork: eliciting must not have touched the shared transcript
				assert not any("PRIVATE aside" in e["content"] for e in st["events"])
	assert marks_seen == [4, 8, 12, 16, 20]


def test_negotiation_solo_arm():
	scen = Negotiation()
	inst = scen.generate_instance(0, 11)
	st = scen.make_state(inst, "solo", 0)
	reqs = scen.next_requests(st)
	assert reqs[0].phase == "solo_work"
	assert "ALL PRIVATE SHEETS" in reqs[0].view[-1]["content"]
	scen.apply(st, reqs[0], '```json\n{"final": ' + json.dumps(inst.solution["best_deal"]) + "}\n```")
	assert st["done"]
	assert scen.score(st)["success"]


def test_negotiation_situational_knobs():
	scen = Negotiation()
	inst = scen.generate_instance_n(6, seed=3)
	st = scen.make_state(inst, "team", 0, cfg={"stakes": "500m", "personas": "one_greedy", "n_rounds": 8})
	assert "career-defining" in scen.system_prompt(st, 0)
	assert "ruthless" in scen.system_prompt(st, 2)          # the one greedy seat
	assert "ruthless" not in scen.system_prompt(st, 3)
	assert "8 rounds" in scen.system_prompt(st, 0)
	assert st["personas"][2] == "greedy"
	with pytest.raises(ValueError):
		persona_assignment("mixed", 4, 0)   # mixed needs a party count divisible by 3


# --- role coherence ---------------------------------------------------------------------------------------

def test_coherent_instances_have_no_conflicts_and_hit_feasible_buckets():
	"""Coherent instances: every priored role x issue slot has the sheet's own-best option OUTSIDE the role's
	disfavored set, and the feasible-set size still lands in the level's target bucket."""
	scen = Negotiation()
	for level in range(scen.N_LEVELS):
		lo, hi = LEVEL_BUCKETS[level]
		for k in range(50):
			inst = scen.generate_instance(level, 500000 + level * 1000 + k, coherent=True)
			p = inst.payload
			assert lo <= p["feasible_count"] <= hi, (level, p["feasible_count"])
			assert conflicted_slots(p["sheets"], p["issues"]) == []
			for role_idx, prior in PRIORS.items():
				for i, (issue_name, options) in enumerate(ISSUES):
					pp = prior.get(issue_name)
					if not pp:
						continue
					assert sheet_argmax_option(p["sheets"][role_idx][i], options) not in pp["disfavor"]


def test_incoherent_generator_still_available():
	"""coherent=False reproduces the original (conflict-bearing) generator."""
	scen = Negotiation()
	assert any(conflicted_slots(scen.generate_instance(0, 600000 + k, coherent=False).payload["sheets"],
	                            scen.generate_instance(0, 600000 + k, coherent=False).payload["issues"])
	           for k in range(20))


# --- info relay -------------------------------------------------------------------------------------------

def test_relay_generation_ladder_and_arithmetic():
	scen = InfoRelay()
	for level in range(5):
		for i in range(4):
			inst = scen.generate_instance(level, level * 10000 + i)
			p = inst.payload
			assert p["hops"] == HOPS[level]
			assert p["n_distract"] == N_DISTRACT[level]
			v = p["values"]
			# solver check: the recorded gold follows from the shard values
			fam = p["family"]
			a = v.get("A", v.get("A1", 0) + v.get("A2", 0))
			b = v.get("B", v.get("B1", 0) + v.get("B2", 0)) if p["hops"] == 4 else v["B"]
			x = a * b if fam == 0 else (a // b if fam == 1 else a - b)
			assert x == v["X_true"]
			gold = x * v["D"] if fam == 0 else (x + v["D"] if fam == 1 else v["D"] - x)
			assert gold == p["gold"]
			# the wrong shard must stay pivotal
			assert abs(p["gold"] - p["answer_wrong"]) > TOL * abs(p["gold"])


def test_relay_prompt_knobs():
	scen = InfoRelay()
	inst = scen.generate_instance(0, 7)
	w = inst.payload["W"]
	for framing in FRAMINGS:
		st = scen.make_state(inst, "team", 0, cfg={"framing": framing})
		assert FRAMINGS[framing]["scene"].split(".")[0] in scen.system_prompt(st, 0)
	st = scen.make_state(inst, "team", 0, cfg={"honest_persona": "skeptical", "wrong_persona": "confident"})
	for si in range(4):
		sp = scen.system_prompt(st, si)
		if si == w:
			assert WRONG_PERSONA["confident"] in sp and HONEST_PERSONA["skeptical"] not in sp
		else:
			assert HONEST_PERSONA["skeptical"] in sp and WRONG_PERSONA["confident"] not in sp
	st0 = scen.make_state(inst, "team", 0, cfg={"cell": "base"})
	for si in range(4):
		for t in list(HONEST_PERSONA.values()) + list(WRONG_PERSONA.values()):
			assert t not in scen.system_prompt(st0, si)
	st2 = scen.make_state(inst, "team", 0, cfg={"n_rounds": 8})
	assert "up to 8 rounds" in scen.system_prompt(st2, 1)


def test_relay_scoring_and_challenges():
	scen = InfoRelay()
	inst = scen.generate_instance(0, 11)
	gold, wrong = inst.payload["gold"], inst.payload["answer_wrong"]
	w_name = scen.make_state(inst, "team", 0)["seat_names"][inst.payload["W"]]

	def play(answer, challenge_w=False):
		st = scen.make_state(inst, "team", 0)
		while not st["done"]:
			req = scen.next_requests(st)[0]
			if req.phase == "final_answer":
				scen.apply(st, req, f'```json\n{{"answer": {answer}}}\n```')
			else:
				text = "Sharing my notes."
				if challenge_w and req.seat != w_name and req.meta["si"] != 0:
					text += f'\n```json\n{{"challenge": {{"target": "{w_name}", "reason": "recompute"}}}}\n```'
				scen.apply(st, req, text)
		return scen.score(st)

	out = play(gold)
	assert out["success"] and not out["wrong_adopted"]
	out = play(wrong)
	assert not out["success"] and out["wrong_adopted"]
	out = play(gold, challenge_w=True)
	assert out["corrected"] and len(out["challenges"]) >= 1


def test_relay_legacy_instances_use_stored_shards():
	scen = InfoRelay()
	inst = scen.generate_instance(0, 3)
	# simulate a first-generation instance: strip the ladder/framing keys, keep rendered text
	legacy_payload = {k: v for k, v in inst.payload.items() if k not in ("n_distract", "conf_tier")}
	inst.payload = legacy_payload
	st = scen.make_state(inst, "team", 0)
	assert st["shards"] == legacy_payload["shards"]
	with pytest.raises(ValueError):
		scen.make_state(inst, "team", 0, cfg={"framing": "high"})
