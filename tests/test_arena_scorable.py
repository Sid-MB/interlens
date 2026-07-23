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


# --- a view-aware scripted seat (one participant plays every seat) ----------------------------------------

def _seat_of(view: list[dict]) -> str:
	system = view[0]["content"]
	if "neutral mediator" in system:
		return "Mediator"
	for name in PERSONAS:
		if f"You are {name}" in system:
			return name
	raise AssertionError(f"could not identify seat from system prompt: {system[:120]!r}")


class JsonSeat(Participant):
	"""One participant that plays every seat, emitting the scenario's fenced-JSON action decided by a per-seat
	policy ``decide(seat_name, view) -> dict`` (the JSON object)."""

	self_role = "assistant"
	others_role = "user"

	def __init__(self, decide):
		self.name = "scripted"
		self.decide = decide

	def generate(self, view, *, steering=None, capture=None, patch=None, return_logprobs=False,
	             turn=None, max_new_tokens=None) -> Message:
		if steering is not None or capture is not None or patch is not None or return_logprobs:
			raise NotImplementedError("JsonSeat has no model")
		obj = self.decide(_seat_of(view), view)
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
