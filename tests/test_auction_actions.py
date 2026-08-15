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

"""The auction move vocabulary, the bid ledger's purity and round-trip, DM routing and its cap, side-payment
settlement, and the parser's syntax/legality split (design.md §3.2, §3.3, §12 item 2)."""
from __future__ import annotations

import json

import pytest

from interlens.arena.actions import LEGALITY, SYNTAX
from interlens.arena.auction import actions as A


# --------------------------------------------------------------------- ledger ---
def _replay(actions, n_items=3, activity_rule="none"):
    led = A.BidLedger(n_items, activity_rule=activity_rule)
    for seat, act, stage, rnd in actions:
        led.apply(act, seat, stage=stage, round=rnd)
    return led


def test_bid_ledger_tracks_the_standing_high_and_keeps_superseded_bids():
    led = _replay([(0, A.Bid(0, 10), 1, 1), (1, A.Bid(0, 20), 1, 1), (2, A.Bid(0, 5), 1, 2)])
    assert led.standing(0, 1).seat == 1 and led.standing(0, 1).amount == 20
    assert len(led.stage_bids(1)) == 3                     # nothing is deleted
    assert led.standing_prices(1) == [20, 0, 0]
    assert led.standing_winners(1) == [1, None, None]
    assert led.standing(0, 2) is None                      # stages do not leak into each other


def test_an_equal_bid_never_dislodges_the_standing_high_bidder():
    """Strict supersession: an equal amount is not a raise. Under the previous `<=` the later equal bid won,
    so a lot went to whichever seat the wave applied last — dict order deciding the auction."""
    led = _replay([(0, A.Bid(0, 10), 1, 1), (1, A.Bid(0, 10), 1, 1)])
    assert led.standing(0, 1).seat == 0                    # first at that amount keeps it
    assert len(led.stage_bids(1)) == 2                     # the loser's bid is still recorded...
    assert [b.live for b in led.stage_bids(1)] == [True, False]
    # ...and the tie's loser is NOT treated as having passed, so the ratchet does not shut it out.
    assert led.eligible(1, 0, 1)


def test_bid_ledger_is_a_pure_function_of_the_action_sequence():
    seq = [(0, A.Bid(0, 10), 1, 1), (1, A.Bid(1, 15), 1, 1), (0, A.PassLot(2), 1, 1),
           (2, A.Exit(), 1, 2), (1, A.Bid(0, 25), 2, 1)]
    a, b = _replay(seq), _replay(seq)
    assert a.to_json() == b.to_json()
    assert A.BidLedger.from_json(json.loads(json.dumps(a.to_json()))).to_json() == a.to_json()


def test_eligibility_ratchet_binds_only_where_the_activity_rule_is_on():
    ratchet = _replay([(0, A.PassLot(1), 1, 1)], activity_rule="eligibility_ratchet")
    assert not ratchet.eligible(0, 1, 1)
    assert ratchet.eligible(0, 2, 1) and ratchet.eligible(1, 1, 1) and ratchet.eligible(0, 1, 2)
    loose = _replay([(0, A.PassLot(1), 1, 1)])
    assert loose.eligible(0, 1, 1)


def test_exits_are_recorded_and_shrink_the_active_set():
    led = _replay([(2, A.Exit(), 1, 3), (4, A.Exit(), 1, 4)])
    assert led.active_seats(1, 5) == [0, 1, 3]
    assert led.active_seats(2, 5) == [0, 1, 2, 3, 4]


def test_action_json_round_trip_for_every_kind():
    for act in (A.Bid(1, 20), A.PassLot(2), A.Schedule((9, 5, 1)), A.Demand(2), A.Stay(), A.Exit(),
                A.Claim(), A.Wait(), A.Speak("hello"), A.DirectMessage(("Aster",), "deal?"),
                A.Transfer("Aster", 30)):
        assert A.auction_action_from_json(json.loads(json.dumps(act.to_json()))) == act
    with pytest.raises(ValueError):
        A.auction_action_from_json({"action": "propose"})


# ------------------------------------------------------------------- DM router ---
def test_dm_router_delivers_privately_enforces_the_cap_and_counts_drops():
    router = A.DMRouter(("A", "B", "C", "D"), dm_cap=2)
    made = router.route(A.DirectMessage(("B", "C", "D"), "let's split"), "A", stage=1, round=1)
    assert [r.recipient for r in made] == ["B", "C"]       # third recipient is over the cap
    assert router.dropped == 1
    assert [r.text for r in router.inbox("B")] == ["let's split"]
    assert router.inbox("D") == []                         # privacy is structural, not tag-dependent
    assert router.graph() == {("A", "B"): 1, ("A", "C"): 1}


def test_dm_router_drops_unknown_and_self_addressed_recipients():
    router = A.DMRouter(("A", "B"), dm_cap=2)
    assert router.route(A.DirectMessage(("A", "Z"), "x"), "A", stage=1, round=1) == []
    assert router.dropped == 2
    assert A.DMRouter.from_json(router.to_json()).to_json() == router.to_json()


def test_transfer_book_executes_only_what_the_sender_can_cover():
    book = A.TransferBook()
    book.declare(A.Transfer("B", 30), "A", stage=1)
    book.declare(A.Transfer("B", 500), "A", stage=1)       # an unpayable promise: weak-cartel behaviour
    net = book.settle(1, {"A": 100.0, "B": 0.0})
    assert net == {"A": -30.0, "B": 30.0}
    assert [r["executed"] for r in book.declared] == [True, False]
    assert A.TransferBook.from_json(book.to_json()).declared == book.declared


# --------------------------------------------------------------------- parsing ---
def test_parser_accepts_a_bare_single_lot_bid():
    r = A.parse_auction_action('{"action": "bid", "amount": 210}', family="sealed_single",
                               item_names=("Lot 1",), budget=300)
    assert r.ok and r.action == A.Bid(item=0, amount=210)


def test_parser_resolves_a_lot_by_name_or_index():
    for ref in ('"Lot 2"', "1"):
        r = A.parse_auction_action('{"action": "bid", "item": %s, "amount": 20}' % ref, family="saa",
                                   item_names=("Lot 1", "Lot 2"))
        assert r.ok and r.action.item == 1


@pytest.mark.parametrize("text,kind,fragment", [
    ("no json here", SYNTAX, "No JSON object"),
    ('{"message": "hi"}', SYNTAX, "No action named"),
    ('{"action": "propose", "deal": [1]}', SYNTAX, "Unknown or illegal action"),
    ('{"action": "bid", "amount": 10.5}', SYNTAX, "whole number"),
    ('{"action": "bid", "item": "Lot 9", "amount": 10}', SYNTAX, "Unknown lot"),
])
def test_parser_syntax_failures_carry_a_specific_retry_message(text, kind, fragment):
    r = A.parse_auction_action(text, family="sealed_single", item_names=("Lot 1",))
    assert not r.ok and r.error_kind == kind and fragment in r.error
    assert r.retry_directive() == {"retry": r.error, "error_kind": kind}


def test_parser_legality_failures_are_distinguished_from_syntax():
    below = A.parse_auction_action('{"action": "bid", "amount": 11}', family="saa",
                                   item_names=("Lot 1",), standing=[10], increment=5)
    assert not below.ok and below.error_kind == LEGALITY and "at least 15" in below.error
    over = A.parse_auction_action('{"action": "bid", "amount": 400}', family="sealed_single",
                                  item_names=("Lot 1",), budget=300)
    assert not over.ok and over.error_kind == LEGALITY and "budget" in over.error
    grain = A.parse_auction_action('{"action": "bid", "amount": 13}', family="sealed_single",
                                   item_names=("Lot 1",), granularity=5)
    assert not grain.ok and grain.error_kind == LEGALITY and "multiples of 5" in grain.error
    passed = A.parse_auction_action('{"action": "bid", "amount": 50}', family="saa",
                                    item_names=("Lot 1",), eligible=lambda j: False)
    assert not passed.ok and passed.error_kind == LEGALITY and "passed on" in passed.error


def test_bidding_above_own_value_is_not_a_parse_error_at_all():
    """Economic errors are MEASURED, never blocked (design.md §3.2) -- which is why the parser never sees a
    seat's valuations."""
    r = A.parse_auction_action('{"action": "bid", "amount": 10000}', family="sealed_single",
                               item_names=("Lot 1",))
    assert r.ok and r.action.amount == 10000


def test_schedule_must_be_weakly_decreasing_and_within_budget():
    ok = A.parse_auction_action('{"action": "schedule", "amounts": [9, 5, 1]}', family="uniform_price",
                                item_names=("Lot 1",), n_units=3)
    assert ok.ok and ok.action == A.Schedule((9, 5, 1))
    rising = A.parse_auction_action('{"action": "schedule", "amounts": [1, 5, 9]}', family="uniform_price",
                                    item_names=("Lot 1",), n_units=3)
    assert not rising.ok and rising.error_kind == LEGALITY and "weakly decreasing" in rising.error
    wrong_len = A.parse_auction_action('{"action": "schedule", "amounts": [9, 5]}', family="uniform_price",
                                       item_names=("Lot 1",), n_units=3)
    assert not wrong_len.ok and wrong_len.error_kind == SYNTAX


def test_demand_is_bounded_by_supply_and_by_budget():
    ok = A.parse_auction_action('{"action": "demand", "units": 2}', family="clinching",
                                item_names=("Lot 1",), n_units=3, clock_price=10, budget=100)
    assert ok.ok and ok.action == A.Demand(2)
    too_many = A.parse_auction_action('{"action": "demand", "units": 5}', family="clinching",
                                      item_names=("Lot 1",), n_units=3)
    assert not too_many.ok and too_many.error_kind == SYNTAX
    broke = A.parse_auction_action('{"action": "demand", "units": 3}', family="clinching",
                                   item_names=("Lot 1",), n_units=3, clock_price=100, budget=100)
    assert not broke.ok and broke.error_kind == LEGALITY


def test_clock_moves_parse_and_are_family_gated():
    assert A.parse_auction_action('{"action": "claim"}', family="dutch", item_names=("Lot 1",)).ok
    assert A.parse_auction_action('{"action": "exit"}', family="english", item_names=("Lot 1",)).ok
    wrong = A.parse_auction_action('{"action": "claim"}', family="english", item_names=("Lot 1",))
    assert not wrong.ok and wrong.error_kind == SYNTAX


def test_nested_action_shape_is_accepted_alongside_the_flat_one():
    r = A.parse_auction_action('{"message": "hi", "action": {"type": "bid", "amount": 42}}',
                               family="sealed_single", item_names=("Lot 1",))
    assert r.ok and r.action == A.Bid(0, 42)


def test_envelope_splits_the_four_channels():
    env = A.parse_envelope('{"scratchpad": "private", "message": "public", '
                           '"dm": [{"to": ["Aster"], "text": "deal?"}], '
                           '"transfer": {"to": "Aster", "amount": 30}, "action": "bid", "amount": 3}')
    assert env.scratchpad == "private" and env.message == "public"
    assert env.dms == [A.DirectMessage(("Aster",), "deal?")]
    assert env.transfer == A.Transfer("Aster", 30)
    empty = A.parse_envelope("nothing here")
    assert empty.message == "" and empty.dms == [] and empty.transfer is None
