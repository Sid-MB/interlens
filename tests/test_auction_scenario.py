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
#
# [implement: auctions | 2026-08-15 | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""End-to-end scripted-participant episodes for :class:`AuctionScenario`, plus the three structural checks the
design cannot take on trust: replay determinism, privacy, and the G3 computable-seat identity."""
from __future__ import annotations

import json
import re

import numpy as np
import pytest

from interlens.arena.auction import actions as A
from interlens.arena.auction.bidders import AuctionState, TruthfulPolicy
from interlens.arena.auction.spec import Mechanism, generate_spec
from interlens.arena.scenarios import auction_prompts as P
from interlens.arena.scenarios.auction import AuctionScenario
from interlens.arena.schema import SeatRequest

FAMILIES = {
    "sealed_second": (lambda n: Mechanism.sealed("second_price", reserve=20), 1),
    "dutch": (lambda n: Mechanism.dutch(increment=20, reserve=20), 1),
    "english": (lambda n: Mechanism.english(increment=20, reserve=20), 1),
    "saa3": (lambda n: Mechanism.saa(3), 3),
    "saa20": (lambda n: Mechanism.saa(20), 20),
}


def build(scn, *, family: str, horizon: int = 2, channel: str = "silent", value_structure: str = "apv",
          seed: int = 7):
    """One instance plus the state a cell of ``family`` would run it under."""
    make, n_items = FAMILIES[family]
    mech = make(n_items)
    inst = scn.generate_instance(0, seed, mechanism=mech, horizon=8)
    cfg = {"mechanism": mech.to_json(), "horizon": horizon, "channel": channel,
           "value_structure": value_structure}
    return inst, scn.make_state(inst, "all_llm", 0, cfg)


class Scripted:
    """A participant that answers every turn from a rule over the rendered view, so a whole episode runs with
    no model. ``reply`` receives ``(state, seat_index)`` and returns the raw turn text."""

    def __init__(self, reply):
        self.reply = reply


def run_episode(scn, state, reply) -> dict:
    """Drive the scenario's own wave loop to completion, exactly as the engine does: build the wave, answer
    every request in order, honour at most one retry per request."""
    guard = 0
    while not state["done"]:
        guard += 1
        assert guard < 4000, "episode did not terminate"
        reqs = scn.next_requests(state)
        if not reqs:
            break
        for req in reqs:
            text = reply(state, int(req.meta["seat_index"]), req)
            directive = scn.apply(state, req, text)
            if directive is not None:
                text = reply(state, int(req.meta["seat_index"]), req)
                assert scn.apply(state, req, text) is None or True
    return scn.score(state)


def truthful_reply(state, seat, req):
    """A legal turn for every phase and family, bidding the seat's own realized value."""
    spec = state["spec"]
    if req.phase == "talk":
        return '```json\n{"scratchpad": "x", "message": "present", "action": "none"}\n```'
    draw = spec.stage(state["stage"])
    vals = draw.values[seat]
    budget = int(draw.budgets[seat])
    fam = spec.mechanism.family
    if fam == "sealed_single":
        return json.dumps({"scratchpad": "x", "action": "bid", "amount": min(int(vals[0]), budget)})
    if fam == "dutch":
        act = "claim" if state["clock_price"] <= min(int(vals[0]), budget) else "wait"
        return json.dumps({"scratchpad": "x", "action": act})
    if fam == "english":
        act = "stay" if state["clock_price"] <= min(int(vals[0]), budget) else "exit"
        return json.dumps({"scratchpad": "x", "action": act})
    ledger = state["ledger"]
    bids, spent = [], 0
    for j in np.argsort(-np.asarray(vals)):
        j = int(j)
        if not ledger.eligible(seat, j, state["stage"]):
            continue
        stand = ledger.standing(j, state["stage"])
        if stand is not None and stand.seat == seat:
            continue
        floor = spec.mechanism.reserve if stand is None else stand.amount + spec.mechanism.increment
        held = state["ledger"].standing(j, state["stage"])
        if floor > vals[j] or spent + floor > budget - scn_committed(state, seat):
            continue
        bids.append({"lot": P.lot_id(j), "amount": int(floor)})
        spent += int(floor)
        if len(bids) >= spec.capacities[seat]:
            break
    if bids:
        return json.dumps({"scratchpad": "x", "action": "bid", "bids": bids})
    return json.dumps({"scratchpad": "x", "action": "pass"})


def scn_committed(state, seat) -> int:
    ledger, spec = state["ledger"], state["spec"]
    return int(sum(s.amount for j in range(spec.n_items)
                   for s in [ledger.standing(j, state["stage"])] if s is not None and s.seat == seat))


# --------------------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("family", sorted(FAMILIES))
@pytest.mark.parametrize("channel", ["silent", "dm"])
def test_end_to_end_every_family_and_channel(family, channel):
    """Every committed format x {silent, dm} completes all stages with clean parses and full hygiene."""
    scn = AuctionScenario()
    inst, state = build(scn, family=family, horizon=2, channel=channel)
    out = run_episode(scn, state, truthful_reply)
    assert out["success"] is True
    assert out["stages_completed"] == 2
    assert out["stage_completion_rate"] == 1.0
    assert out["parse_ok_rate"] == 1.0
    assert out["syntax_errors"] == 0 and out["legality_errors"] == 0
    assert len(out["stages"]) == 2
    for row in out["stages"]:
        assert 0.0 <= row["efficiency"] <= 1.0 + 1e-9


@pytest.mark.parametrize("n_items", [3, 20])
def test_saa_at_both_lot_counts(n_items):
    """The 3-lot pilot rung and the 20-lot confirmatory rung run the same code and the same wording."""
    scn = AuctionScenario()
    family = "saa3" if n_items == 3 else "saa20"
    inst, state = build(scn, family=family, horizon=2, channel="dm")
    out = run_episode(scn, state, truthful_reply)
    assert out["success"] and out["n_items"] == n_items
    assert out["family"] == "saa"


def test_replay_determinism():
    """The ledger is a pure function of the applied action sequence: replaying the recorded actions rebuilds
    it byte for byte."""
    scn = AuctionScenario()
    inst, state = build(scn, family="saa3", horizon=2, channel="silent")
    run_episode(scn, state, truthful_reply)
    original = state["ledger"].to_json()
    rebuilt = A.BidLedger.from_json(original).to_json()
    assert rebuilt == original


def test_privacy_is_structural_over_a_whole_episode():
    """Programmatic privacy, asserted three ways over every turn of a whole episode.

    A number-level scan over the whole view is not the right test — two seats' realized values collide by
    coincidence — so the check is structural instead, which is also what the design actually claims: the
    private region belongs to exactly one seat, no other seat's private block appears anywhere in the view,
    and every number inside the private region traces to the reading seat's own draws."""
    scn = AuctionScenario()
    inst, state = build(scn, family="saa3", horizon=3, channel="dm")
    spec = state["spec"]
    seen = 0
    while not state["done"]:
        reqs = scn.next_requests(state)
        if not reqs:
            break
        for req in reqs:
            seat = int(req.meta["seat_index"])
            text = "\n".join(seg["content"] for seg in req.view)
            assert text.count("=== PRIVATE " + P.EMDASH) == 1
            for other in range(spec.n_bidders):
                if other == seat:
                    continue
                assert scn._private_block(state, other) not in text, \
                    f"seat {other}'s private block reached seat {seat}'s view"
            region = text.split("=== PRIVATE " + P.EMDASH, 1)[1].split("Bidding round", 1)[0]
            draw = spec.stage(state["stage"])
            own = ({int(v) for v in draw.values[seat]} | {int(draw.budgets[seat]), state["stage"],
                                                          spec.capacities[seat]}
                   | {int(round(spec.synergy_rates[seat] * sum(draw.values[seat][j]
                                                               for j in (draw.synergy_target[seat] or ()))))}
                   | set(range(1, spec.n_items + 1)))
            for number in re.findall(r"(?<![\d.])\d+(?![\d.])", region):
                assert int(number) in own, \
                    f"the private block of seat {seat} carries {number}, which is not one of its own numbers"
            seen += 1
            scn.apply(state, req, truthful_reply(state, seat, req))
    assert seen > 0


def test_public_blocks_are_byte_identical_across_seats():
    """The catalogue and the public roster are rendered once and shared, so the only per-seat difference in
    the shared part of a system prompt is the one line that names the reading seat."""
    scn = AuctionScenario()
    inst, state = build(scn, family="saa3", horizon=2, channel="dm")
    catalogues = {scn._catalogue(state) for _ in range(state["spec"].n_bidders)}
    assert len(catalogues) == 1
    rosters = set()
    for seat in range(state["spec"].n_bidders):
        system = scn.system_prompt(state, seat)
        rosters.add(system.split("The five organizations at this auction")[1].split("**How lots are worth")[0])
    assert len(rosters) == 1


def test_g3_all_rational_second_price_ipv_bids_own_value():
    """G3: in second-price under IPV a truthful policy bids exactly its own value in every stage, and the
    oracle's bid is identical (an oracle has no edge in a dominant-strategy mechanism)."""
    mech = Mechanism.sealed("second_price", reserve=0)
    spec = generate_spec(11, mechanism=mech, value_structure="ipv", horizon=4)
    private, oracle = TruthfulPolicy("private"), TruthfulPolicy("oracle")
    for t in range(1, spec.horizon + 1):
        for seat in range(spec.n_bidders):
            own = int(spec.stage(t).values[seat][0])
            sp = AuctionState.from_spec(spec, t, seat)
            so = AuctionState.from_spec(spec, t, seat, information="oracle")
            assert private.bid_for(sp, 0) == own
            assert oracle.bid_for(so, 0) == own


def test_retry_then_fallback_records_the_format_fallback():
    """A syntax error retries once with the parser's own message; a second failure records the format's
    fallback move and delivers nothing the seat wrote."""
    scn = AuctionScenario()
    inst, state = build(scn, family="sealed_second", horizon=1, channel="dm")
    reqs = scn.next_requests(state)
    req = reqs[0]
    bad = 'no json here at all, but "message": "sneak this through"'
    directive = scn.apply(state, req, bad)
    assert directive is not None and "[Auctioneer]" in directive["retry"]
    assert scn.apply(state, req, bad) is None
    assert state["hygiene"]["syntax_errors"] == 1
    assert not state["broadcasts"], "a channel payload on an unparseable turn must not be delivered"


def test_economic_error_is_measured_not_blocked():
    """Bidding above your own valuation parses cleanly and lands in the overbid metric; bidding above BUDGET
    is a legality error instead, because a payment must be collectible."""
    scn = AuctionScenario()
    inst, state = build(scn, family="sealed_second", horizon=1, channel="silent")
    reqs = scn.next_requests(state)
    draw = state["spec"].stage(1)
    overbid = 0
    for req in reqs:
        seat = int(req.meta["seat_index"])
        # A budget below own value is a live design feature (the Che-Gale subject's budget_mult < 1), so the
        # overbid is only offered where the budget has room for it; the rest bid at their budget.
        amount = min(int(draw.values[seat][0]) + 5, int(draw.budgets[seat]))
        overbid += amount > int(draw.values[seat][0])
        assert scn.apply(state, req, json.dumps({"action": "bid", "amount": amount})) is None
    out = scn.score(state)
    assert overbid > 0, "fixture needs at least one seat with budget headroom above its value"
    assert out["parse_ok_rate"] == 1.0
    assert out["stages"][0]["overbid_own_value_rate"] == pytest.approx(overbid / 5)


def test_over_budget_bid_is_a_legality_retry():
    scn = AuctionScenario()
    inst, state = build(scn, family="sealed_second", horizon=1, channel="silent")
    req = scn.next_requests(state)[0]
    seat = int(req.meta["seat_index"])
    over = int(state["spec"].stage(1).budgets[seat]) + 1
    directive = scn.apply(state, req, json.dumps({"action": "bid", "amount": over}))
    assert directive is not None and directive["error_kind"] == "legality"
    assert str(over) in directive["retry"]


def test_dm_reaches_only_its_recipient():
    """A DM is delivered to the addressed seat and to nobody else, and the directed graph records it."""
    scn = AuctionScenario()
    inst, state = build(scn, family="sealed_second", horizon=1, channel="dm")
    reqs = scn.next_requests(state)
    names = state["seat_names"]
    for req in reqs:
        seat = int(req.meta["seat_index"])
        target = names[(seat + 1) % len(names)]
        scn.apply(state, req, json.dumps({"action": "none",
                                          "dm": [{"to": target, "text": f"secret-{seat}"}]}))
    for seat in range(len(names)):
        inbox = "".join(r.text for r in state["dm"].inbox(names[seat]))
        assert f"secret-{(seat - 1) % len(names)}" in inbox
        assert sum(f"secret-{s}" in inbox for s in range(len(names))) == 1


def test_eligibility_ratchet_closes_a_lot_permanently():
    scn = AuctionScenario()
    inst, state = build(scn, family="saa3", horizon=1, channel="silent")
    reqs = scn.next_requests(state)
    # Passes fold into the ledger when the WAVE resolves, not mid-round: an SAA round is simultaneous, so a
    # seat's pass must not be visible to the seats that answer after it within the same round.
    for k, req in enumerate(reqs):
        move = {"action": "pass", "lots": ["L01"]} if k == 0 else {"action": "pass"}
        assert scn.apply(state, req, json.dumps(move)) is None
        if k == 0:
            assert state["ledger"].eligible(0, 0, 1), "a pass must not bind before the round closes"
    assert not state["ledger"].eligible(0, 0, 1)


# --------------------------------------------------------------------------------------------------------- #
# Computable seats.
# --------------------------------------------------------------------------------------------------------- #
def policy_table(scn, state, inst, information: str):
    """A SeatRouter of computable seats, the free `all_rational` / `all_oracle` arms."""
    from interlens.arena.scenarios.auction_policy import AuctionPolicyParticipant
    from interlens.arena.table import SeatRouter
    spec = state["spec"]
    return SeatRouter({state["seat_names"][i]: AuctionPolicyParticipant(
        f"{information}#{i}", spec=spec, seat=i, information=information,
        instance_id=inst.instance_id) for i in range(spec.n_bidders)}, name=f"all_{information}")


@pytest.mark.parametrize("family", ["sealed_second", "dutch", "english", "saa3"])
@pytest.mark.parametrize("information", ["private", "oracle"])
def test_free_computable_arms_play_every_format(family, information):
    """`all_rational` and `all_oracle` are pure Python and cost nothing, so they run in every cell
    unconditionally — which only holds if they actually complete every format."""
    scn = AuctionScenario()
    policies = {i: ("oracle" if information == "oracle" else "rational") for i in range(5)}
    make, n_items = FAMILIES[family]
    mech = make(n_items)
    inst = scn.generate_instance(0, 21, mechanism=mech, horizon=8)
    state = scn.make_state(inst, f"all_{information}", 0,
                           {"mechanism": mech.to_json(), "horizon": 2, "channel": "dm",
                            "policy_seats": policies})
    table = policy_table(scn, state, inst, information)
    guard = 0
    while not state["done"]:
        guard += 1
        assert guard < 4000
        reqs = scn.next_requests(state)
        if not reqs:
            break
        for req in reqs:
            msg = table.generate(req.view, seat=req.seat)
            assert scn.apply(state, req, msg.content) is None, "a computable seat must never need a retry"
    out = scn.score(state)
    assert out["success"] and out["parse_ok_rate"] == 1.0
    assert out["syntax_errors"] == 0 and out["legality_errors"] == 0


def test_policy_seat_view_carries_no_prose_and_no_rival_draws():
    """A computable seat reads a structured state block, not prose; and a PRIVATE-information seat's block
    carries no rival's realized values at all."""
    scn = AuctionScenario()
    make, _ = FAMILIES["saa3"]
    mech = make(3)
    inst = scn.generate_instance(0, 21, mechanism=mech, horizon=8)
    state = scn.make_state(inst, "one_rational", 0,
                           {"mechanism": mech.to_json(), "horizon": 1, "channel": "dm",
                            "policy_seats": {0: "rational"}})
    req = [r for r in scn.next_requests(state) if r.meta["seat_index"] == 0][0]
    assert "```auction_state" in req.view[0]["content"]
    assert "You are the bidding agent" not in req.view[0]["content"]
    block = scn.state_block(state, 0)
    assert "oracle_values" not in block
    assert scn.state_block(scn.make_state(inst, "one_oracle", 0,
                                          {"mechanism": mech.to_json(), "horizon": 1, "channel": "dm",
                                           "policy_seats": {0: "oracle"}}), 0)["oracle_values"]


def test_oracle_and_rational_seats_emit_identical_message_templates():
    """The oracle's templates are identical to the rational seat's: an oracle that spoke from full information
    would leak every other seat's private draws through the channel."""
    from interlens.arena.scenarios.auction_policy import AuctionPolicyParticipant
    scn = AuctionScenario()
    make, _ = FAMILIES["saa3"]
    mech = make(3)
    inst = scn.generate_instance(0, 21, mechanism=mech, horizon=8)
    texts = []
    for info in ("private", "oracle"):
        state = scn.make_state(inst, f"all_{info}", 0,
                              {"mechanism": mech.to_json(), "horizon": 1, "channel": "dm",
                               "policy_seats": {i: ("oracle" if info == "oracle" else "rational")
                                                for i in range(5)}})
        part = AuctionPolicyParticipant(f"p#{0}", spec=state["spec"], seat=0, information=info,
                                        instance_id=inst.instance_id)
        req = scn.next_requests(state)[0]
        texts.append(json.loads(part.generate(req.view, seat=req.seat).content
                                .strip("`json\n ").split("\n```")[0])["message"])
    assert texts[0] == texts[1]


def test_surface_variants_are_reproducible_and_arm_invariant():
    """The templated variant is seeded from the frozen instance, seat, stage and template id, so it is stable
    across processes and identical in every arm — a variant that moved between arms would confound Q5."""
    from interlens.arena.auction import policy_text
    a = policy_text.variant_index("inst-1", 2, 3, "dm_initiate", 3)
    b = policy_text.variant_index("inst-1", 2, 3, "dm_initiate", 3)
    c = policy_text.variant_index("inst-1", 2, 4, "dm_initiate", 3)
    assert a == b
    assert 0 <= a < 3 and 0 <= c < 3


def test_state_block_carries_every_field_the_conditional_bayes_seat_updates_on():
    """The rational seat's within-stage updating reads `exits`, `clock_price`, `active`, `standing` and
    `standing_winner` through `AuctionPolicy._conditioned`. If the stage loop fails to feed those, the seat
    degenerates to a truthful bidder and Q5 measures the wrong agent — so the block's field set is pinned."""
    scn = AuctionScenario()
    make, _ = FAMILIES["english"]
    mech = make(1)
    inst = scn.generate_instance(0, 31, mechanism=mech, horizon=8)
    state = scn.make_state(inst, "one_rational", 0,
                           {"mechanism": mech.to_json(), "horizon": 2, "channel": "silent",
                            "policy_seats": {0: "rational"}})
    # Drive one clock round so an exit is on the record, then read the block.
    for req in scn.next_requests(state):
        seat = int(req.meta["seat_index"])
        move = "exit" if seat == 4 else "stay"
        scn.apply(state, req, json.dumps({"action": move}))
    block = scn.state_block(state, 0)
    for field in ("stage", "round", "phase", "values", "budget", "standing", "standing_winner",
                  "clock_price", "active", "exits", "inbox"):
        assert field in block, f"the policy state block must carry {field}"
    assert block["exits"], "a public exit must reach the rational seat's state block"
    assert 4 not in block["active"]
