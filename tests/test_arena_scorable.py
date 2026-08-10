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

# [rational_agents scaffold: scenario-runner] 2026-07-23 — ScorableNegotiation state-machine smoke.

"""ScorableNegotiation protocol smoke: the repaired-protocol invariants (real votes, offer-id references, WALK,
IR-violation accounting, the solo control), plus engine integration (retry, save, replay/rescore-identical) and
the per-turn oracle-input hook. No GPU, no API, no network — one participant drives every seat via a
view-aware scripted policy that emits the scenario's fenced-JSON action format.

The game is a hand-built 3-party / 2-issue :class:`GameSpec` with known surpluses, so every assertion is exact:
- (North, High) clears all three thresholds -> a clean deal.
- (North, Low)  leaves party 1 below threshold -> accepting it is an individual-rationality violation.
"""
from __future__ import annotations

import asyncio
import json
import re

import pytest

from interlens.arena.engine import EpisodePool
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet
from interlens.arena.negotiation.space import DealSpace, Issue
from interlens.arena.replay import rescore
from interlens.arena.schema import Instance, EpisodeStore, PERSONAS, new_id
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.message import Message
from interlens.participant.participant import Participant


# --- the fixed game ---------------------------------------------------------------------------------------

def make_game(rounds: int = 4, info: str = "full", chat: bool = True, veto: int | None = None) -> GameSpec:
	space = DealSpace((Issue("Site", ("North", "South")), Issue("Fund", ("Low", "Mid", "High"))))
	sheets = (
		ScoreSheet("Alpha", ((10.0, 0.0), (0.0, 3.0, 6.0)), threshold=5.0),   # wants North
		ScoreSheet("Beta", ((0.0, 10.0), (0.0, 3.0, 6.0)), threshold=5.0),    # wants South
		ScoreSheet("Gamma", ((5.0, 5.0), (6.0, 3.0, 0.0)), threshold=3.0),    # site-agnostic, wants Low fund
	)
	return GameSpec(space, sheets, rounds=rounds, info=info, chat=chat, proposer=0, veto=veto, min_accept=None)


def make_instance(spec: GameSpec) -> Instance:
	return Instance(new_id("scorable-test"), ScorableNegotiation.name, 0, 0,
	                payload=spec.to_json(), ceiling=1.0, floor=0.0, solution={})


# --- a scripted seat (one participant plays every seat, dispatching on the engine-passed seat) --------------

class JsonSeat(Participant):
	"""One participant that plays every seat, emitting the scenario's fenced-JSON action decided by a per-seat
	policy ``decide(seat_name, view) -> dict`` (the JSON object)."""

	self_role = "assistant"
	others_role = "user"

	def __init__(self, decide):
		self.name = "scripted"
		self.decide = decide

	def generate(self, view, *, steering=None, capture=None, patch=None, return_logprobs=False,
	             turn=None, max_new_tokens=None, seat: str | None = None) -> Message:
		if steering is not None or capture is not None or patch is not None or return_logprobs:
			raise NotImplementedError("JsonSeat has no model")
		assert seat is not None, "the arena engine must pass the seat identity"
		obj = self.decide(seat, view)
		return Message(self.name, "```json\n" + json.dumps(obj) + "\n```")


def _first_offer_id(view: list[dict]) -> str | None:
	m = re.search(r"\bP\d+\b", view[-1]["content"])
	return m.group(0) if m else None


def coop(target: dict):
	"""Propose ``target`` if nothing is on the table yet, else accept the first live offer id seen."""
	def decide(seat, view):
		oid = _first_offer_id(view)
		if oid is None or "none yet" in view[-1]["content"]:
			return {"scratchpad": "open with the target package",
			        "message": "I propose this package.", "action": "propose", "deal": target}
		return {"message": f"{oid} works for me.", "action": "accept", "offer_id": oid}
	return decide


def run(scenario, instance, arm, participant, cfg=None, store=None, budget=None):
	pool = EpisodePool(store)
	return asyncio.run(pool.run_episode(scenario, instance, arm, participant, seed=0, cfg=cfg, budget=budget))


def drive_state(scenario, instance, arm, decide, cfg=None):
	"""Step the pure state machine directly (no engine) so a test can inspect ``state`` — notably the public
	``events`` log, which is exactly what other seats' views are built from. Honors the one-retry directive."""
	st = scenario.make_state(instance, arm, seed=0, cfg=cfg)
	for _guard in range(400):
		if st["done"]:
			break
		reqs = scenario.next_requests(st)
		if not reqs:
			break
		for req in reqs:
			text = "```json\n" + json.dumps(decide(req.seat, req.view)) + "\n```"
			directive = scenario.apply(st, req, text)
			if directive and "retry" in directive:
				scenario.apply(st, req, "```json\n" + json.dumps(decide(req.seat, req.view)) + "\n```")
	return st


# --- tests ------------------------------------------------------------------------------------------------

def test_deal_forms_by_unanimous_vote():
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	ep = run(scen, inst, "moves_chat", JsonSeat(coop({"Site": "North", "Fund": "High"})))
	out = ep.outcome
	assert out["deal"] is True and out["success"] is True
	assert out["finalized_by"] == "consensus"
	# a real vote closed it: every active party accepted the closing offer
	closing = out["closing_offer"]
	assert closing is not None
	assert set(out["support_final"][closing]) == set(PERSONAS[:3])
	# (North, High): surpluses Alpha=11, Beta=1, Gamma=2 — all clear, no IR violation
	assert out["per_party_surplus"] == [11.0, 1.0, 2.0]
	assert out["n_ir_violations"] == 0
	assert 0.0 < out["primary"] <= 1.0
	assert out["deal_named"] == {"Site": "North", "Fund": "High"}


def test_primary_is_invariant_to_per_party_positive_affine_rescaling():
	base = make_game()
	scales = (2.0, 7.0, 0.5)
	offsets = (100.0, -30.0, 11.0)
	scaled_sheets = []
	for sheet, a, b in zip(base.sheets, scales, offsets):
		values = [list(row) for row in sheet.values]
		for j, row in enumerate(values):
			values[j] = [a * value + (b if j == 0 else 0.0) for value in row]
		scaled_sheets.append(ScoreSheet(sheet.agent, tuple(tuple(row) for row in values),
		                               threshold=a * sheet.threshold + b))
	scaled = GameSpec(base.space, tuple(scaled_sheets), rounds=base.rounds, info=base.info, chat=base.chat,
	                  proposer=base.proposer, veto=base.veto, min_accept=base.min_accept)
	scenario = ScorableNegotiation()
	base_state = scenario.make_state(make_instance(base), "moves_chat", seed=0)
	scaled_state = scenario.make_state(make_instance(scaled), "moves_chat", seed=0)
	deal = (0, 2)  # North, High
	assert scenario._deal_primary(base_state, deal, set()) == pytest.approx(
		scenario._deal_primary(scaled_state, deal, set()))
	base_state["final_deal"] = scaled_state["final_deal"] = deal
	base_out, scaled_out = scenario.score(base_state), scenario.score(scaled_state)
	assert base_out["primary"] == scaled_out["primary"]
	assert base_out["normalized_realized_surplus"] == scaled_out["normalized_realized_surplus"]
	assert "raw_primary" in base_out and "ceiling_surplus" in base_out


def test_ir_violation_recorded_but_not_blocked():
	# (North, Low): Beta scores 0 < threshold 5 — accepting it is an IR violation that must be MEASURED, not
	# blocked or retried (Design Lesson 12).
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	ep = run(scen, inst, "moves_chat", JsonSeat(coop({"Site": "North", "Fund": "Low"})))
	out = ep.outcome
	assert out["deal"] is True                       # the deal still forms — the bad choice stands
	assert out["ir_violations"] == [PERSONAS[1]]     # seat 1 (Beta's sheet) accepted below its threshold
	assert out["n_ir_violations"] == 1
	assert out["economic_errors"] >= 1               # a below-threshold offer was accepted
	assert out["per_party_surplus"][1] == -5.0


def test_channel_separation_is_structural():
	# Privacy lives in the PUBLIC event log (what other seats' views are built from), never in tag discipline.
	# The scratchpad must never appear there; in moves_only the cheap-talk message must not either.
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	target = {"Site": "North", "Fund": "High"}

	def decide(seat, view):
		oid = _first_offer_id(view)
		if oid is None or "none yet" in view[-1]["content"]:
			return {"scratchpad": "SECRET-PLAN-DO-NOT-LEAK", "message": "PUBLIC-HELLO",
			        "action": "propose", "deal": target}
		return {"scratchpad": "SECRET-PLAN-DO-NOT-LEAK", "message": "PUBLIC-HELLO",
		        "action": "accept", "offer_id": oid}

	chat_events = drive_state(scen, inst, "moves_chat", decide)["events"]
	chat_text = "\n".join(e["content"] for e in chat_events)
	assert "SECRET-PLAN-DO-NOT-LEAK" not in chat_text   # scratchpad is never published
	assert "PUBLIC-HELLO" in chat_text                  # the cheap-talk message is, when chat is on

	mo_events = drive_state(scen, inst, "moves_only", decide)["events"]
	mo_text = "\n".join(e["content"] for e in mo_events)
	assert "SECRET-PLAN-DO-NOT-LEAK" not in mo_text     # scratchpad never leaks, in either arm
	assert "PUBLIC-HELLO" not in mo_text                # the cheap-talk channel is off in moves_only
	# formal moves ARE public in both arms (they are how a moves-only game communicates) — the action shows
	assert '"action": "propose"' in mo_text or '"action":"propose"' in mo_text


def test_walk_of_veto_party_forces_no_deal():
	scen = ScorableNegotiation()
	inst = make_instance(make_game(rounds=2, veto=2))   # Gamma (seat 2) holds the veto

	def decide(seat, view):
		if seat == PERSONAS[2]:                         # the veto seat walks out
			return {"message": "I'm leaving.", "action": "walk"}
		return coop({"Site": "North", "Fund": "High"})(seat, view)

	ep = run(scen, inst, "moves_chat", JsonSeat(decide))
	out = ep.outcome
	assert PERSONAS[2] in out["walked"]
	assert out["deal"] is False and out["success"] is False
	assert out["finalized_by"] == "no_deal"


def test_solo_control_runs_and_scores():
	scen, inst = ScorableNegotiation(), make_instance(make_game())

	def decide(seat, view):
		return {"action": "propose", "deal": {"Site": "North", "Fund": "High"}}

	ep = run(scen, inst, "solo", JsonSeat(decide))
	assert ep.status == "done"
	assert ep.outcome["arm"] == "solo"
	assert ep.outcome["deal"] is True
	assert ep.outcome["deal_named"] == {"Site": "North", "Fund": "High"}


def test_syntax_error_retried_then_passes():
	scen, inst = ScorableNegotiation(), make_instance(make_game(rounds=1))
	state = {"n": 0}

	def decide(seat, view):
		# the very first turn emits a propose with no deal -> a syntax error -> one retry; then cooperate
		if state["n"] == 0:
			state["n"] += 1
			return {"action": "propose"}   # missing "deal" -> parse_action SYNTAX -> one retry
		return coop({"Site": "North", "Fund": "High"})(seat, view)

	ep = run(scen, inst, "moves_chat", JsonSeat(decide))
	assert ep.outcome["syntax_errors"] >= 1
	assert ep.status == "done"


def test_save_replay_rescore_is_identical(tmp_path):
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	store = EpisodeStore(tmp_path)
	ep = run(scen, inst, "moves_chat", JsonSeat(coop({"Site": "North", "Fund": "High"})), store=store)
	# the episode was persisted; replay its stored turns through a fresh state machine and rescore
	saved = json.loads(store.path(ep).read_text())
	result = rescore(scen, inst, saved)
	assert result["match"], result
	assert result["recomputed"]["primary"] == ep.outcome["primary"]


def test_self_elicitation_populates_round_checkpoints():
	scen, inst = ScorableNegotiation(), make_instance(make_game(rounds=3))

	def decide(seat, view):
		# always table the target (so the provisional "finalize now" is scored on a valid deal)
		return {"action": "propose", "deal": {"Site": "North", "Fund": "High"}}

	ep = run(scen, inst, "moves_chat", JsonSeat(decide), cfg={"self_elicit": True})
	assert ep.round_checkpoints, "self-elicitation should attach per-turn provisional annotations"
	assert all("score" in c and "provisional_action" in c for c in ep.round_checkpoints)


def test_oracle_inputs_shape_midgame():
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	st = scen.make_state(inst, "moves_chat", seed=0)
	ctx = scen.oracle_inputs(st)
	assert set(ctx) == {"game", "agent", "history", "legal_actions"}
	assert isinstance(ctx["game"], GameSpec)
	assert ctx["agent"] == 0 and isinstance(ctx["agent"], int)   # seat index (oracles accept it as-is)
	# legal actions are typed Action objects; WALK is always available (no live offers yet)
	kinds = {a.kind for a in ctx["legal_actions"]}
	assert "walk" in kinds


def test_oracle_annotation_attaches_to_turns():
	# a stub oracle exercises the annotate_turn engine plumbing: every turn should carry an OracleRecord.
	from interlens.arena.oracles import Oracle, OracleVerdict

	class StubOracle(Oracle):
		name = "stub"

		def evaluate(self, game, history, agent, legal):
			# value every legal action at 0.0 and call the first one "best" — enough to record a divergence
			values = {a: 0.0 for a in legal}
			best = legal[0] if legal else None
			return OracleVerdict(action_values=values, best=best, flags=["stub"])

	scen = ScorableNegotiation(oracles=[StubOracle()])
	ep = run(scen, make_instance(make_game()), "moves_chat", JsonSeat(coop({"Site": "North", "Fund": "High"})))
	assert ep.round_checkpoints, "oracle annotations should attach to turns"
	rec = ep.round_checkpoints[0]
	assert rec.get("oracle") == "stub" and "divergence" in rec


def test_full_vs_private_info_changes_common_knowledge():
	scen = ScorableNegotiation()
	full = scen.make_state(make_instance(make_game(info="full")), "moves_chat", 0)
	priv = scen.make_state(make_instance(make_game(info="private")), "moves_chat", 0)
	sys_full = scen._system_prompt(full, 0)
	sys_priv = scen._system_prompt(priv, 0)
	# under FULL info every party's sheet is common knowledge (the all-sheets block appears); under PRIVATE
	# only the acting seat's own sheet does.
	assert "common knowledge" in sys_full
	assert "All parties' score sheets" in sys_full
	assert "All parties' score sheets" not in sys_priv
	assert "private to them" in sys_priv


def test_view_persisted_in_turn_records():
	# the engine records the exact rendered view each turn was conditioned on (default on), so a transcript is
	# faithful even if prompt code later drifts — no reconstruction-by-replay needed.
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	ep = run(scen, inst, "moves_chat", JsonSeat(coop({"Site": "North", "Fund": "High"})))
	assert ep.turns and all(t.view for t in ep.turns)
	first = ep.turns[0]
	assert first.view[0]["role"] == "system"                     # the seat's system prompt leads the view
	assert ep.to_json()["turns"][0]["view"] == first.view        # it round-trips into the episode JSON


def test_view_recording_can_be_disabled():
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	pool = EpisodePool(None, record_views=False)
	ep = asyncio.run(pool.run_episode(scen, inst, "moves_chat",
	                                  JsonSeat(coop({"Site": "North", "Fund": "High"})), seed=0))
	assert ep.turns and all(t.view is None for t in ep.turns)    # lean mode: no views stored


# --- seeded opening offer ------------------------------------------------------------------------------------
# [implement: rational_agents orig (results review)--optimal on the table] 2026-08-10 — the `seeded_offer`
# protocol knob: one standing package tabled by a neutral non-voting facilitator before round 1.

SEEDED_DEAL = {"Site": "North", "Fund": "High"}          # clears all three thresholds
SEED_CFG = {"seeded_offer": {"deal": SEEDED_DEAL, "kind": "ceiling", "source": "unit-test"}}


def _accept_seeded(seat, view):
	"""Accept the facilitator's offer (always P1) on every turn, in whatever phase."""
	return {"message": "P1 works for me.", "action": "accept", "offer_id": "P1"}


def test_seeded_offer_is_registered_and_announced_before_any_seat_speaks():
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	st = scen.make_state(inst, "moves_chat", seed=0, cfg=SEED_CFG)
	offers = st["registry"].standing()
	assert len(offers) == 1 and offers[0].offer_id == "P1"
	assert offers[0].deal == (0, 2)                        # North, High
	assert offers[0].proposer == "Facilitator"
	assert offers[0].accepts == set()                      # the facilitator casts NO implicit vote
	assert st["seeded_offer"]["kind"] == "ceiling" and st["seeded_offer"]["offer_id"] == "P1"
	# announced publicly, before any turn, and attributed to the non-seat facilitator
	assert st["events"] and st["events"][0]["seat"] == "Facilitator"
	assert "P1" in st["events"][0]["content"] and "casts no vote" in st["events"][0]["content"]
	# and it is visible in the machine-readable state block every seat reads
	from interlens.arena.negotiation.strategies import parse_negotiation_state
	state = parse_negotiation_state(scen._state_block_json(st, 0))
	assert state["offers"]["P1"] == [0, 2] and state["standing"] == "P1"
	assert state["offer_proposers"]["P1"] == -1           # no seat proposed it
	assert state["offer_accepts"]["P1"] == []
	# a facilitator package reveals nothing about any party, so it never enters the opponent-modelling inputs
	assert state["received"] == [] and state["received_by_opponent"] == {}


def test_seeded_offer_needs_every_seat_and_the_facilitator_never_counts():
	# Two of three seats accept; the facilitator's registration must not supply the third vote.
	scen, inst = ScorableNegotiation(), make_instance(make_game(rounds=1))

	def decide(seat, view):
		if seat == PERSONAS[2]:
			return {"message": "Not yet.", "action": "reject", "offer_id": "P1"}
		return _accept_seeded(seat, view)

	st = drive_state(scen, inst, "moves_chat", decide, cfg=SEED_CFG)
	out = scen.score(st)
	assert out["deal"] is False
	assert sorted(st["registry"].get("P1").accepts) == sorted(PERSONAS[:2])


def test_seeded_offer_closes_on_unanimous_acceptance():
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	ep = run(scen, inst, "moves_chat", JsonSeat(_accept_seeded), cfg=SEED_CFG)
	out = ep.outcome
	assert out["deal"] is True and out["closing_offer"] == "P1"
	assert out["deal_named"] == SEEDED_DEAL
	assert out["seeded_offer"]["final_is_seeded"] is True
	assert out["seeded_offer"]["kind"] == "ceiling"
	assert sorted(out["seeded_offer"]["accepts"]) == sorted(PERSONAS[:3])


def test_seeded_single_shot_is_one_forced_vote_by_every_seat():
	# V-vote: the seeded offer IS the final offer, so no seat proposes and EVERY seat casts an up/down vote.
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	cfg = {**SEED_CFG, "single_shot": True}
	st = drive_state(scen, inst, "moves_chat", _accept_seeded, cfg=cfg)
	out = scen.score(st)
	assert out["deal"] is True and out["closing_offer"] == "P1"
	assert sorted(st["final_votes"]) == sorted(PERSONAS[:3])     # all three voted, including the opener
	assert st["turn_count"] == 3                                 # exactly one turn per seat
	assert all(o.proposer == "Facilitator" for o in st["registry"].standing())


def test_seeded_single_shot_one_refusal_kills_the_deal():
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	cfg = {**SEED_CFG, "single_shot": True}

	def decide(seat, view):
		if seat == PERSONAS[1]:
			return {"message": "No.", "action": "reject", "offer_id": "P1"}
		return _accept_seeded(seat, view)

	st = drive_state(scen, inst, "moves_chat", decide, cfg=cfg)
	out = scen.score(st)
	assert out["deal"] is False and out["finalized_by"] == "no_deal"
	assert out["seeded_offer"]["final_is_seeded"] is False
	assert PERSONAS[1] in out["seeded_offer"]["rejects"]


@pytest.mark.parametrize("single_shot", [False, True])
def test_seeded_episode_replays_exactly(single_shot):
	# G1: the seed lives in cfg (hence in the stored cell_cfg) and is applied in make_state, so replaying the
	# stored action sequence reconstructs the same state and rescores identically.
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	cfg = {**SEED_CFG, "single_shot": single_shot}
	ep = run(scen, inst, "moves_chat", JsonSeat(_accept_seeded), cfg=cfg)
	report = rescore(ScorableNegotiation(), inst, ep.to_json())
	assert report["match"], report


def test_seeded_offer_rejects_a_malformed_deal():
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	for bad in ({"Site": "North"}, {"Site": "Nowhere", "Fund": "High"}, [0, 9], [0]):
		with pytest.raises(ValueError):
			scen.make_state(inst, "moves_chat", seed=0, cfg={"seeded_offer": {"deal": bad}})


def test_unseeded_game_is_untouched():
	scen, inst = ScorableNegotiation(), make_instance(make_game())
	st = scen.make_state(inst, "moves_chat", seed=0, cfg={"seeded_offer": None})
	assert st["registry"].standing() == [] and st["events"] == [] and st["seeded_offer"] is None
	assert st["final_offer"] is None and st["final_vote_includes_opener"] is False


def test_ceiling_deal_is_exactly_the_deal_the_scorer_calls_one():
	# GameSpec.normalized_geometry owns both the ceiling VALUE (the scorer's denominator) and the deal that
	# attains it, which is what makes "seed the optimum" well defined: seeding ceiling_deal must score 1.0, and
	# no other feasible deal may beat it.
	game = make_game()
	geom = game.normalized_geometry()
	scen, inst = ScorableNegotiation(), make_instance(game)
	st = scen.make_state(inst, "moves_chat", seed=0)
	assert geom["ceiling_deal"] is not None
	assert scen._deal_primary(st, geom["ceiling_deal"], set()) == pytest.approx(1.0)
	mask = game.feasible_mask()
	for k, deal in enumerate(game.space.enumerate()):
		if mask[k]:
			assert scen._deal_primary(st, tuple(deal), set()) <= 1.0 + 1e-9
	# and it is what the ceiling-seeded protocol actually tables
	seeded = scen.make_state(inst, "moves_chat", seed=0,
	                         cfg={"seeded_offer": {"deal": list(geom["ceiling_deal"]), "kind": "ceiling"}})
	assert tuple(seeded["seeded_offer"]["deal"]) == geom["ceiling_deal"]


def test_single_shot_state_block_reports_the_terminal_round():
	# The forced final is the LAST decision point, and a policy that plans against the clock reads its horizon
	# off the state block. Under single_shot the regular rounds never run, so the state's own counter is still
	# 1 — the block must report the round of the PHASE being requested (deadline+1), or an expectimax seat
	# values a terminal vote against rounds of continuation that do not exist.
	scen, inst = ScorableNegotiation(), make_instance(make_game(rounds=4))
	cfg = {**SEED_CFG, "single_shot": True}
	st = scen.make_state(inst, "moves_chat", seed=0, cfg=cfg)
	req = scen.next_requests(st)[0]
	assert req.phase == "final_vote" and req.round == 5
	from interlens.arena.negotiation.strategies import parse_negotiation_state
	state = parse_negotiation_state(req.view[-1]["content"])
	assert (state["round"], state["deadline"], state["must_vote"]) == (5, 4, True)
	# the ordinary game already advanced its own counter, so its forced final is unchanged
	plain = drive_state(scen, make_instance(make_game(rounds=1)), "moves_chat",
	                    lambda seat, view: {"action": "propose", "deal": SEEDED_DEAL})
	assert plain["round"] == 2


# --- the turn-cap protocol option ---------------------------------------------------------------------------
# [rational_agents: uncap-protocol] 2026-08-10 — session eb951d8f. The per-turn output cap is a PROTOCOL
# VERSION, not a tuning knob: at the frozen 2,048 a thinking-ON model burns the whole budget inside <think> and
# the engine substitutes a placeholder (notes 0026/0041), so a raised-cap run measures different behaviour and
# must not be pooled with a default-cap one. These tests pin both halves of that: the default is untouched so
# every frozen campaign still reproduces, and the option reaches the actual generation kwarg.

def _all_caps(scen, rounds: int = 2) -> list[tuple[str, int]]:
	"""Every ``(phase, max_tokens)`` the scenario stamps across a whole episode, incl. the forced final."""
	inst, caps = make_instance(make_game(rounds=rounds)), []
	st = scen.make_state(inst, "moves_chat", seed=0)
	for _guard in range(400):
		if st["done"]:
			break
		reqs = scen.next_requests(st)
		if not reqs:
			break
		for req in reqs:
			caps.append((req.phase, req.max_tokens))
			# always propose, never accept: nothing closes early, so the walk reaches the forced final AND the
			# final up/down vote (where a propose is merely illegal, which still emits the request being measured)
			scen.apply(st, req, "```json\n" + json.dumps(
				{"action": "propose", "deal": {"Site": "North", "Fund": "High"}}) + "\n```")
	return caps


def test_default_turn_caps_are_unchanged():
	# The frozen protocol every published five-seat campaign ran. If this ever moves, no old run reproduces.
	caps = dict(_all_caps(ScorableNegotiation()))
	assert caps["turn"] == 2048
	assert caps["final_proposal"] == 2560
	assert caps["final_vote"] == 2048
	assert ScorableNegotiation().turn_max_tokens is None


def test_turn_max_tokens_raises_every_phase_and_never_shrinks_the_final():
	scen = ScorableNegotiation(turn_max_tokens=32768)
	assert {cap for _phase, cap in _all_caps(scen)} == {32768}
	# below the protocol's own numbers it is a floor, not an assignment: the forced final keeps its larger cap
	lowered = dict(_all_caps(ScorableNegotiation(turn_max_tokens=100)))
	assert (lowered["turn"], lowered["final_proposal"]) == (2048, 2560)
	with pytest.raises(ValueError):
		ScorableNegotiation(turn_max_tokens=0)


def test_turn_max_tokens_reaches_the_generation_kwarg():
	# The engine's own turn_cap can only SHRINK a request's cap, so this is the only path that widens the real
	# max_new_tokens. Asserting on the kwarg (not the request) is what makes this a threading test.
	seen: list[int | None] = []

	class RecordingSeat(JsonSeat):
		def generate(self, view, *, max_new_tokens=None, **kw):
			seen.append(max_new_tokens)
			return super().generate(view, max_new_tokens=max_new_tokens, **kw)

	inst = make_instance(make_game(rounds=1))
	decide = lambda seat, view: {"action": "none"}     # noqa: E731 — every turn a no-op; the caps are the point
	run(ScorableNegotiation(turn_max_tokens=32768), inst, "moves_chat", RecordingSeat(decide))
	assert seen and set(seen) == {32768}
	seen.clear()
	run(ScorableNegotiation(), inst, "moves_chat", RecordingSeat(decide))
	assert set(seen) == {2048, 2560}
