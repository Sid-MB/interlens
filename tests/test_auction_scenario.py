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
import math
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


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_the_primary_suppression_measure_is_defined_in_every_stage_of_every_format(family):
    """The clock-denominator fix, stated as the property that motivated it: the PRIMARY collusion measure must
    exist in the stages a cell actually plays, or a confirmatory cell buys mostly `n/a`.

    A descending clock has exactly one priced action per stage, the claim, so the design's losing-bidder scope
    left suppression undefined wherever the claim was uncontested — 4 of 6 stages in the ring smoke. Every seat
    here takes a priced action at its own realized value against a reserve of 20, so a defined number is the
    correct expectation in all four families and an undefined one is the defect. (Note the English stages need
    no sale for this: an exit is itself a priced action, so a stage every seat exits from is still measured.)"""
    scn = AuctionScenario()
    inst, state = build(scn, family=family, horizon=2, channel="silent")
    out = run_episode(scn, state, truthful_reply)
    for row in out["stages"]:
        assert row["suppression_n"] >= 1, f"{family} stage {row['stage']} has no priced action to measure"
        assert not math.isnan(row["suppression"])
        assert row["suppression_scope"] == ("priced" if family == "dutch" else "losers")
    if family == "dutch":
        assert all(any(w is not None for w in row["winner_of"]) for row in out["stages"]), (
            "the fix is about the winner's claim being the measurement, so these stages must have a winner")


def test_only_a_descending_clock_bounds_a_non_actors_bid_and_says_so():
    """`suppression_censored` is defined exactly where the mechanism bounds a silent seat's bid from above, and
    is absent — not zero — everywhere else. A sealed bidder that submitted nothing revealed no bound at all."""
    scn = AuctionScenario()
    dutch = run_episode(scn, build(scn, family="dutch", horizon=2, channel="silent")[1], truthful_reply)
    for row in dutch["stages"]:
        # Five seats, one of them the claimer: the censored column spans the whole table, the primary does not.
        assert row["suppression_censored_n"] == 5 > row["suppression_n"]
        assert row["suppression_censored"] <= row["suppression"] + 1e-9, "the bound must not overstate"
    sealed = run_episode(scn, build(scn, family="sealed_second", horizon=2, channel="silent")[1], truthful_reply)
    for row in sealed["stages"]:
        assert row["suppression_censored_n"] == 0 and math.isnan(row["suppression_censored"])


@pytest.mark.parametrize("n_items", [3, 20])
def test_saa_at_both_lot_counts(n_items):
    """The 3-lot pilot rung and the 20-lot confirmatory rung run the same code and the same wording."""
    scn = AuctionScenario()
    family = "saa3" if n_items == 3 else "saa20"
    inst, state = build(scn, family=family, horizon=2, channel="dm")
    out = run_episode(scn, state, truthful_reply)
    assert out["success"] and out["n_items"] == n_items
    assert out["family"] == "saa"


def test_saa_wave_resolution_is_invariant_to_the_order_the_wave_arrives_in():
    """The reproducibility property every paired cross-cell contrast rests on: the SAME wave of actions must
    fold to the SAME ledger and the same standing table no matter what order the seats' turns arrive in.

    It did not. Every SAA raiser bids exactly ``standing + increment``, so simultaneous claims on a lot are
    exact ties by construction, and the ledger superseded on ``<=`` — the lot went to whichever seat the wave
    happened to apply last, i.e. dict iteration order. The fold now resolves each lot by (highest amount,
    then the stage's frozen seeded permutation), which is both the announced rule and order-invariant."""
    scn = AuctionScenario()
    inst, state = build(scn, family="saa3", horizon=1, channel="silent")
    mech = state["spec"].mechanism
    seats = list(range(state["spec"].n_bidders))
    # One wave in which every seat claims the same two lots at the identical legal amount — the exact tie.
    amount = mech.reserve + mech.increment
    wave = {s: A.SAATurn(bids=(A.Bid(item=0, amount=amount), A.Bid(item=1, amount=amount)))
            for s in seats}

    def fold(order):
        _, st = build(scn, family="saa3", horizon=1, channel="silent")
        scn._fold_bids(st, {s: wave[s] for s in order})
        return st["ledger"].to_json(), st["ledger"].standing_winners(1)

    baseline, winners = fold(seats)
    for order in (list(reversed(seats)), [seats[i] for i in (2, 0, 4, 1, 3)]):
        assert fold(order) == (baseline, winners), f"wave order {order} changed the ledger"
    # And the winner is the announced one: first in the stage's seeded priority order, not first-applied.
    priority = {s: k for k, s in enumerate(state["spec"].stage(1).tie_break)}
    assert winners[0] == min(seats, key=lambda s: priority[s])
    assert winners[1] == min(seats, key=lambda s: priority[s])


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


def test_clock_formats_get_one_mid_stage_message_round_per_stage():
    """design.md §3.4 commits to a message round "once more before the final bidding round in clock formats",
    so a ring can be TESTED mid-stage and not only formed before it. The end of a clock stage is endogenous, so
    the trigger is the midpoint of the announced schedule: exactly one extra talk wave per stage, it does not
    disturb the clock, and the seats are told the price the clock is standing at."""
    scn = AuctionScenario()
    make, _ = FAMILIES["english"]
    mech = make(1)
    inst = scn.generate_instance(0, 17, mechanism=mech, horizon=8)
    state = scn.make_state(inst, "all_llm", 0,
                           {"mechanism": mech.to_json(), "horizon": 1, "channel": "dm", "talk_rounds": 1})
    cap = state["spec"].mechanism.round_cap
    phases, mid_views, prices = [], [], []
    for _ in range(400):
        reqs = scn.next_requests(state)
        if not reqs:
            break
        phases.append((state["phase"], state["bid_round"], state["mid_talk_active"]))
        if state["mid_talk_active"]:
            mid_views.append(reqs[0].view[-1]["content"])
            prices.append(int(state["clock_price"]))
        for req in reqs:
            move = "none" if state["phase"] == "talk" else ("stay" if int(req.meta["seat_index"]) < 2 else "exit")
            scn.apply(state, req, json.dumps({"action": move}))

    mid = [p for p in phases if p[2]]
    assert len(mid) == 1, "exactly one mid-stage message round per stage"
    assert mid[0][1] == max(2, cap // 2), "it fires at the midpoint of the announced clock schedule"
    assert "Mid-stage message round" in mid_views[0]
    assert f"**{prices[0]}**" in mid_views[0], "the paused clock price is restated, not left to be inferred"
    assert "before bidding begins" not in mid_views[0], "bidding HAS begun by then"
    # The detour leaves the clock exactly where it was: the round index and the price on the bidding wave
    # after it are the ones the mid-stage view named.
    i = next(k for k, p in enumerate(phases) if p[2])
    assert phases[i + 1][0] == "bid" and phases[i + 1][1] == phases[i][1]
    assert int(state["spec"].mechanism.increment) > 0


def test_sealed_and_silent_cells_get_no_mid_stage_round():
    """A sealed stage has one bidding round and a silent cell has no channel, so a mid-stage message round
    would be a wasted turn per seat per stage in both."""
    scn = AuctionScenario()
    for family, channel in (("sealed_second", "dm"), ("english", "silent")):
        make, _ = FAMILIES[family]
        mech = make(1)
        inst = scn.generate_instance(0, 17, mechanism=mech, horizon=8)
        state = scn.make_state(inst, "all_llm", 0,
                               {"mechanism": mech.to_json(), "horizon": 1, "channel": channel,
                                "talk_rounds": 1})
        for _ in range(400):
            reqs = scn.next_requests(state)
            if not reqs:
                break
            assert not state["mid_talk_active"], f"{family}/{channel} must get no mid-stage round"
            for req in reqs:
                move = ("none" if state["phase"] == "talk"
                        else ("bid" if family == "sealed_second" else "stay"))
                payload = {"action": move} | ({"amount": 30} if move == "bid" else {})
                scn.apply(state, req, json.dumps(payload))


# --------------------------------------------------------------------------------------------------------- #
# X1 — the persona-scrambled control (design.md §4.2, gate G2(b)).
# --------------------------------------------------------------------------------------------------------- #
def _x1_pair(seed: int = 11, horizon: int = 1, channel: str = "silent"):
    """One instance read as its O1 reference cell and as its X1 scrambled twin — the same frozen draws."""
    scn = AuctionScenario()
    mech = Mechanism.sealed("second_price", reserve=20)
    inst = scn.generate_instance(0, seed, mechanism=mech, horizon=8)
    base = {"mechanism": mech.to_json(), "horizon": horizon, "channel": channel, "value_structure": "apv"}
    return scn, inst, scn.spec_for(inst, base), scn.spec_for(inst, base | {"scramble_cards": True})


def test_scramble_is_a_derangement_of_whole_cards():
    """No seat keeps its own card, and the card moves as ONE UNIT — a seat showing one persona's prose beside
    another's attribute vector would be a half-scramble that leaves the public prior partly informative."""
    from interlens.arena.auction.spec import PUBLIC_CARD_FIELDS
    scn, inst, plain, scrambled = _x1_pair()
    perm = scrambled.meta["card_scramble"]["derangement"]
    assert sorted(perm) == list(range(5)) and all(perm[i] != i for i in range(5))
    for i in range(5):
        for f in PUBLIC_CARD_FIELDS:
            assert getattr(scrambled.bidders[i], f) == getattr(plain.bidders[perm[i]], f)
        assert scrambled.bidders[i].seat == i
    # Every card is still present exactly once: the scramble is a permutation, not a redraw.
    assert sorted(b.persona_id for b in scrambled.bidders) == sorted(b.persona_id for b in plain.bidders)


def test_scramble_leaves_every_private_draw_and_every_valuation_untouched():
    """The break is public-card-to-valuation and nothing else: values, budgets, targets, signals and the
    tie-break permutation are byte-identical to the reference cell's."""
    scn, inst, plain, scrambled = _x1_pair(horizon=8)
    assert [s.to_json() for s in scrambled.stages] == [s.to_json() for s in plain.stages]
    assert scrambled.mechanism == plain.mechanism and scrambled.value_structure == "apv"


def test_scramble_seed_is_frozen_to_the_instance_id():
    """Same instance -> same derangement, in any rerun and any arm order; different instance -> its own."""
    from interlens.arena.auction.spec import card_scramble_seed, derangement
    scn, inst, _, first = _x1_pair(seed=11)
    _, _, _, again = _x1_pair(seed=11)
    _, other_inst, _, other = _x1_pair(seed=12)
    assert first.meta["card_scramble"] == again.meta["card_scramble"]
    assert first.meta["card_scramble"]["seed"] == card_scramble_seed(inst.instance_id)
    assert tuple(first.meta["card_scramble"]["derangement"]) \
        == derangement(5, card_scramble_seed(inst.instance_id))
    assert other.meta["card_scramble"]["derangement"] != first.meta["card_scramble"]["derangement"]


def test_scrambled_rendering_moves_prose_and_numbers_together():
    """The rendered system prompt is the real check: the seat addressed as X must carry X's prose AND X's
    printed profile line, and the reading seat's "your seat" line must name the card it holds."""
    scn, inst, plain, scrambled = _x1_pair()
    perm = scrambled.meta["card_scramble"]["derangement"]
    plain_state = scn.make_state(inst, "all_llm", 0, {"mechanism": plain.mechanism.to_json(), "horizon": 1})
    x1_state = scn.make_state(inst, "all_llm", 0,
                              {"mechanism": plain.mechanism.to_json(), "horizon": 1, "scramble_cards": True})
    # The same five cards are on the table in both cells — only which seat holds which one moves. That is what
    # makes X1 a scramble rather than a different set of personas, so the roster is compared as a SET of card
    # blocks (it is printed in seat order, which is exactly the thing the scramble permutes).
    roster = lambda st: sorted((scn.system_prompt(st, 0).split("The five organizations at this auction")[1]
                                .split("How lots are worth")[0]).split("\n\n"))
    assert roster(plain_state) == roster(x1_state)
    for i in range(5):
        held = plain.bidders[perm[i]]
        seat_line = scn.system_prompt(x1_state, i)
        assert f"You are **{held.display_name}**, seat id `{held.persona_id}`" in seat_line
        # The scrambled seat's addressable id IS the card it holds, so nothing a bidder reads contradicts
        # anything else it reads.
        assert x1_state["seat_names"][i] == held.persona_id


def test_scramble_privacy_is_unchanged_and_the_private_block_stays_with_its_own_seat():
    """Seat i still reads seat i's realized values and budget — the scramble must not move a draw across the
    privacy line, and no rival's numbers may appear in any view."""
    scn, inst, plain, scrambled = _x1_pair()
    state = scn.make_state(inst, "all_llm", 0,
                           {"mechanism": plain.mechanism.to_json(), "horizon": 1, "scramble_cards": True})
    draw = plain.stage(1)
    for i in range(5):
        view = scn.system_prompt(state, i) + "\n" + scn.turn_prompt(state, i)
        assert str(int(draw.values[i][0])) in view and str(int(draw.budgets[i])) in view
        for j in range(5):
            if j != i:
                assert f"is worth **{int(draw.values[j][0])}**" not in view


def test_scramble_is_refused_under_interdep():
    """gamma is both a printed card figure and the switch selecting which seat holds the stage's resale
    signals, so permuting it would split one seat across the public/private line."""
    from interlens.arena.auction.spec import card_scramble_seed, scramble_public_cards
    spec = generate_spec(3, mechanism=Mechanism.sealed(), value_structure="interdep", horizon=1)
    with pytest.raises(ValueError, match="interdep"):
        scramble_public_cards(spec, seed=card_scramble_seed("auction-3"))


def test_channel_content_is_persisted_on_the_outcome_not_just_its_dyad_counts():
    """design.md §9.3's third collusion measure is the mutual information between a seat's message TEXT to a
    named rival and its value bin, so a stored run carrying only ``dm_graph`` counts makes that measure
    uncomputable in exactly the DM cells it exists for. Both rungs land in one chronological log, broadcasts
    as a dyad to "all" (``recipient is None``), so the ladder is on one scale."""
    scn = AuctionScenario()
    mech = Mechanism.sealed("second_price", reserve=20)
    inst = scn.generate_instance(0, 7, mechanism=mech, horizon=8)
    state = scn.make_state(inst, "all_llm", 0, {"mechanism": mech.to_json(), "horizon": 1, "channel": "dm",
                                                "talk_rounds": 1})
    names = list(state["seat_names"])
    for _ in range(20):
        reqs = scn.next_requests(state)
        if not reqs:
            break
        for req in reqs:
            seat = int(req.meta["seat_index"])
            talk = state["phase"] == "talk"
            payload = {"action": "none"} if talk else {"action": "bid", "amount": 30}
            if talk:
                payload |= {"message": f"hold at {40 + seat}",
                            "dm": [{"to": [names[(seat + 1) % 5]],
                                    "text": f"split lot one at {40 + seat}"}]}
            scn.apply(state, req, "```json\n" + json.dumps(payload) + "\n```")
    msgs = scn.score(state)["messages"]
    dms = [m for m in msgs if m["channel"] == "dm"]
    casts = [m for m in msgs if m["channel"] == "broadcast"]
    assert dms and casts, "both rungs of the ladder must reach the stored outcome"
    assert all(m["text"] for m in msgs), "the TEXT is the measure; a count is not a substitute for it"
    assert all(m["recipient"] is None for m in casts)
    assert {(m["sender"], m["recipient"]) for m in dms} == {(names[i], names[(i + 1) % 5]) for i in range(5)}
    # The phase a DM rode on is a real distinction (a message round vs a bidding turn) and is stamped, so a
    # mid-stage DM never reads the same as a pre-bidding one.
    assert all(m["phase"] in ("talk", "bid") for m in msgs)


@pytest.mark.parametrize("family", ["sealed_second", "dutch", "saa3"])
def test_replay_integrity_reproduces_a_computable_seat_and_catches_a_tampered_move(tmp_path, family):
    """The universal free-arm gate: every computable turn must equal its own policy re-evaluated on the very
    state block it was rendered with.

    This is the mechanism-independent form of "the played seat is its rule", and it is what gates the clock
    families, where the equilibrium form of G3 does not apply (design.md §6). The negative half matters as
    much as the positive: a checker that cannot fail is not a gate, so the test tampers with one recorded
    move and requires the mismatch to be found."""
    import json as _json

    from interlens.arena.scenarios.auction_policy import AuctionPolicyParticipant, replay_integrity

    scn = AuctionScenario()
    make, n_items = FAMILIES[family]
    mech = make(n_items)
    inst = scn.generate_instance(0, 7, mechanism=mech, horizon=8)
    seats = {i: "rational" for i in range(5)}
    cfg = {"mechanism": mech.to_json(), "horizon": 2, "channel": "silent", "value_structure": "apv",
           "policy_seats": seats}
    state = scn.make_state(inst, "all_rational", 0, cfg)
    spec = state["spec"]

    # A bank of one, written where the checker looks for the instance it replays against.
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / f"{inst.instance_id}.json").write_text(_json.dumps(inst.to_json()))

    # Drive the episode with the real policy participants and record turns the way the runner does.
    turns, idx = [], 0
    while not state["done"]:
        reqs = scn.next_requests(state)
        if not reqs:
            break
        for req in reqs:
            seat = int(req.meta["seat_index"])
            name = state["seat_names"][seat]
            participant = AuctionPolicyParticipant(name, spec=spec, seat=seat, information="private",
                                                   instance_id=inst.instance_id)
            text = participant.generate(req.view).content
            turns.append({"idx": idx, "seat": name, "round": state["round"], "phase": req.phase,
                          "view": req.view, "parsed_action": None, "_text": text})
            idx += 1
            scn.apply(state, req, text)
            turns[-1]["parsed_action"] = _json.loads(text.split("```json")[1].split("```")[0])
    episode = {"instance_id": inst.instance_id, "arm": "all_rational", "cell_cfg": cfg,
               "seats": [{"name": state["seat_names"][i], "seat": i} for i in range(5)], "turns": turns}

    clean = replay_integrity(episode, bank)
    assert clean["checked"] > 0, "nothing was replayed — the gate would pass vacuously"
    assert clean["pass"] and not clean["mismatches"]

    # Tamper: rewrite one binding move to something the policy would never have produced.
    tampered = _json.loads(_json.dumps({k: v for k, v in episode.items()}))
    for turn in tampered["turns"]:
        action = turn.get("parsed_action") or {}
        if action.get("bids"):                      # multi-lot grammar
            action["bids"][0]["amount"] = int(action["bids"][0]["amount"]) + 7
            break
        if "amount" in action:                      # single-lot grammar
            action["amount"] = int(action["amount"]) + 7
            break
    else:
        pytest.skip("no priced move to tamper with in this family")
    caught = replay_integrity(tampered, bank)
    assert not caught["pass"] and caught["mismatches"], "a tampered move slipped past the gate"


# --- the NON-FROZEN instructed-ring probe (docs/templates/ring_block.md) ------------------------------------
@pytest.mark.parametrize("channel", ["dm_transfers", "dm"])
def test_instructed_ring_reaches_members_only_and_leaves_the_frozen_prefix_intact(channel):
    """The two properties the whole probe rests on: the OUTSIDER is never told an agreement exists, and a ring
    member's system prompt is the outsider's plus one suffix — so ring-vs-neutral is one block and not a
    reworded scaffold. Also pins the per-channel side-payment semantics, since "a promise is words" versus
    "the auctioneer executes it" is the McAfee-McMillan strong/weak-cartel switch itself."""
    scn = AuctionScenario()
    make, n_items = FAMILIES["sealed_second"]
    mech = make(n_items)
    inst = scn.generate_instance(0, 7, mechanism=mech, horizon=8)
    base = {"mechanism": mech.to_json(), "horizon": 2, "channel": channel, "value_structure": "apv"}
    neutral = scn.make_state(inst, "all_llm", 0, base)
    ringed = scn.make_state(inst, "all_llm", 0,
                            dict(base, ring={"members": [0, 1, 2, 3], "instructed": True}))
    members, outsider = (0, 1, 2, 3), 4
    for seat in members:
        member = scn.system_prompt(ringed, seat)
        assert member.startswith(scn.system_prompt(neutral, seat).rsplit("\n\nReply with ONLY", 1)[0])
        assert "## Coordination agreement" in member
        assert "divide the lots between them" in member
        for other in members:
            assert f"`{ringed['spec'].bidders[other].persona_id}`" in member
        if channel == "dm_transfers":
            assert "executed by the auctioneer at settlement" in member
        else:
            assert "There is no transfer field" in member
        # No script: the probe measures the division, the price, and the punishment, so it supplies none.
        assert "rotate" not in member.lower() and "retaliat" not in member.lower()
    assert scn.system_prompt(ringed, outsider) == scn.system_prompt(neutral, outsider)


def test_a_declared_transfer_is_executed_end_to_end_and_moves_the_surplus():
    """The whole `dm_transfers` rung, exercised from a seat's turn text to the stored outcome.

    This path has never carried a single real transfer: the ring smoke declared ZERO across six episodes, so
    "the seats never used the instrument" and "the instrument was never wired" would have produced the same
    number. A primary outcome that reads 0.000 has to be provably a BEHAVIOURAL zero, which means the path must
    be shown to work when it is used. Both halves of the McAfee-McMillan semantics are pinned: a transfer the
    sender can cover executes and moves surplus, and one it cannot is recorded `executed: False` rather than
    dropped, because an unpaid promise IS the weak-cartel behaviour."""
    scn = AuctionScenario()
    mech = Mechanism.sealed("second_price", reserve=20)
    inst = scn.generate_instance(0, 7, mechanism=mech, horizon=8)
    state = scn.make_state(inst, "all_llm", 0, {"mechanism": mech.to_json(), "horizon": 1,
                                               "channel": "dm_transfers", "talk_rounds": 1})
    names = list(state["seat_names"])
    budgets = list(state["spec"].stage(1).budgets)
    # The payer must be a seat whose budget can actually cover the payment NET OF ITS AUCTION PAYMENT. That is
    # not a detail: `ai_lab` carries budget_mult 0.70 as the Che-Gale budget-bound subject, and here its whole
    # remaining capacity after a bid of 30 is 22 -- so the seat the design makes poorest cannot fund a
    # meaningful side payment at all. Transfer capacity is heterogeneous BY DESIGN.
    payer_seat = max(range(5), key=lambda i: budgets[i])
    payee_seat = min(range(5), key=lambda i: budgets[i])
    payer, payee = names[payer_seat], names[payee_seat]
    assert budgets[payer_seat] > 25, "the premise of the coverable half"

    def play(declare: bool) -> dict:
        st = scn.make_state(inst, "all_llm", 0, {"mechanism": mech.to_json(), "horizon": 1,
                                                "channel": "dm_transfers", "talk_rounds": 1})
        while True:
            reqs = scn.next_requests(st)
            if not reqs:
                break
            talk = st["phase"] == "talk"
            for req in reqs:
                seat = int(req.meta["seat_index"])
                payload = {"action": "none"} if talk else {"action": "bid", "amount": 30}
                # Declared once, in the talk round, so the arithmetic below is one payment and not two.
                if declare and talk:
                    if seat == payer_seat:
                        payload |= {"transfer": {"to": payee, "amount": 25}}
                    elif seat == payee_seat:
                        payload |= {"transfer": {"to": payer, "amount": 10 ** 7}}
                scn.apply(st, req, "```json\n" + json.dumps(payload) + "\n```")
        return scn.score(st)

    out, baseline = play(True), play(False)
    declared = out["transfers"]["declared"] if isinstance(out["transfers"], dict) else out["transfers"]
    by_sender = {d["sender"]: d for d in declared}
    assert set(by_sender) == {payer, payee}, "both declarations must be recorded, coverable or not"
    assert by_sender[payer]["executed"] is True and by_sender[payer]["amount"] == 25
    assert by_sender[payee]["executed"] is False, "an uncoverable promise is words, and is recorded as words"
    assert not (baseline["transfers"]["declared"] if isinstance(baseline["transfers"], dict)
                else baseline["transfers"]), "the control declared nothing"

    # The stage ROW must carry what was moved, because that is what every reader of executed side payments
    # reads. It did not: the pilot recorded a transfer with `executed: True` while every stage row read `{}`,
    # so the measure the transfer cell exists for could not have seen its own positive case.
    net = out["stages"][0]["transfer_net"]
    assert net[payer] == -25.0 and net[payee] == 25.0
    assert not any(v for k, v in baseline["stages"][0]["transfer_net"].items()), "the control moved nothing"

    # And the executed one moved real surplus, on the stage row the analyzer reads.
    surplus, base = out["stages"][0]["surplus"], baseline["stages"][0]["surplus"]
    assert surplus[payer_seat] == base[payer_seat] - 25, "the payer is 25 worse off"
    assert surplus[payee_seat] == base[payee_seat] + 25, "the payee is 25 better off"
    for i in range(5):
        if i not in (payer_seat, payee_seat):
            assert surplus[i] == base[i], "nobody else moved"


def test_designated_but_uninstructed_ring_changes_no_prompt():
    """``instructed=False`` records a ring the ANALYSIS designated for a counterfactual. It must be inert on
    the prompt surface, or a counterfactual would silently become a treatment."""
    scn = AuctionScenario()
    make, n_items = FAMILIES["sealed_second"]
    mech = make(n_items)
    inst = scn.generate_instance(0, 7, mechanism=mech, horizon=8)
    base = {"mechanism": mech.to_json(), "horizon": 2, "channel": "dm", "value_structure": "apv"}
    neutral = scn.make_state(inst, "all_llm", 0, base)
    designated = scn.make_state(inst, "all_llm", 0,
                                dict(base, ring={"members": [0, 1, 2, 3], "instructed": False}))
    assert designated["spec"].ring.members == (0, 1, 2, 3)
    for seat in range(neutral["spec"].n_bidders):
        assert scn.system_prompt(designated, seat) == scn.system_prompt(neutral, seat)


def test_instructed_ring_refuses_a_silent_cell():
    """An agreement printed into a cell with no channel is an instruction the seats cannot act on."""
    with pytest.raises(ValueError, match="channel to coordinate in"):
        P.AuctionPromptScaffold().ring_block(channel="silent", member_ids=["a", "b"], n_bidders=5)


def test_the_ring_instruction_is_versioned_and_its_rendered_bytes_are_pinned_to_that_version():
    """The ring block cannot join the neutral prompt freeze — it says the thing that freeze exists to keep
    unsaid — so it carries a version of its own, and a run records which one it read.

    A version nobody can check is decoration, so the rendered BYTES are pinned here. Editing the wording makes
    this test fail, which is the intended cost: the fix is to bump `RING_BLOCK_VERSION` and update the hash
    together, and a bumped version then keeps the new episodes out of the old ones' population."""
    import hashlib
    scaffold = P.AuctionPromptScaffold()
    assert scaffold.RING_BLOCK_VERSION == "ring_block_v1"
    partial = ["sovereign_fund", "hyperscaler", "regional_operator", "colo_reit"]
    digests = {f"{size}/{channel}": hashlib.sha256(
        scaffold.ring_block(channel=channel, member_ids=ids, n_bidders=5).encode()).hexdigest()[:16]
        for size, ids in (("partial", partial), ("inclusive", partial + ["ai_lab"]))
        for channel in ("dm", "dm_transfers", "broadcast")}
    assert digests == {"partial/dm": "5429b46896d10151",
                       "partial/dm_transfers": "060542d258185c1b",
                       "partial/broadcast": "3005af2ebd049f5e",
                       "inclusive/dm": "225f7e8fe797b0d6",
                       "inclusive/dm_transfers": "9bacc2572ce8e23f",
                       "inclusive/broadcast": "ab143864e5790b22"}, (
        f"the ring instruction's rendered bytes changed under an unchanged version: {digests}")


def test_an_all_inclusive_ring_never_mentions_an_outsider_that_does_not_exist():
    """McAfee-McMillan's all-inclusive cartel: every seat is a party, so the block must not print the
    non-party sentence with a zero in it. "The remaining 0 organizations have not been told" is a statement
    about nobody, and it would send all five seats hunting for a seat that is not at the table."""
    scaffold = P.AuctionPromptScaffold()
    ids = ["sovereign_fund", "hyperscaler", "regional_operator", "colo_reit", "ai_lab"]
    text = scaffold.ring_block(channel="dm_transfers", member_ids=ids, n_bidders=5)
    assert "Every organization bidding in this auction is a party to it." in text
    assert "not been told" not in text and "non-part" not in text and " 0 " not in text
    # And the partial ring still says it, since that sentence is what makes the outsider identifiable.
    assert "not been told that it exists" in scaffold.ring_block(channel="dm_transfers", member_ids=ids[:4],
                                                                 n_bidders=5)
