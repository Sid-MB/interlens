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

"""The typed formal-action layer: the move dataclasses, the offer registry (ids, standing offers, votes), and
``parse_action``'s single JSON-extraction-and-validation path with its syntax-vs-legality error classes."""
from __future__ import annotations

from interlens.arena.actions import (Accept, LEGALITY, Offer, OfferRegistry, ParsedTurn, ParseResult, Propose,
                                     Reject, SYNTAX, Turn, Walk, action_from_json, parse_action, parse_turn)


def fence(obj: str) -> str:
	return f"```json\n{obj}\n```"


# ---------------------------------------------------------------- actions ---

def test_action_json_round_trip_and_hashable():
	assert Propose(deal=(0, 1, 2)).to_json() == {"action": "propose", "deal": [0, 1, 2]}
	assert Accept(offer_id="O1").to_json() == {"action": "accept", "offer_id": "O1"}
	assert Reject(offer_id="O2").to_json() == {"action": "reject", "offer_id": "O2"}
	assert Walk().to_json() == {"action": "walk"}
	# frozen -> hashable, so actions can key an OracleVerdict.action_values dict
	assert len({Accept("O1"), Accept("O1"), Walk()}) == 2


def test_turn_channel_separation():
	turn = Turn(agent="Avery", thinking="private", action=Accept("O1"), message="I'm in.")
	assert turn.agent == "Avery" and turn.action == Accept("O1") and turn.message == "I'm in."


# ---------------------------------------------------------------- registry ---

def test_registry_monotonic_ids_and_proposer_autoaccept():
	reg = OfferRegistry()
	a = reg.register((0, 0), "Avery", round=1)
	b = reg.register((1, 1), "Blake", round=1)
	assert (a, b) == ("O1", "O2")
	assert reg.get(a).accepts == {"Avery"}          # proposing implies supporting your own offer
	assert reg.standing_ids() == {"O1", "O2"}


def test_registry_votes_and_withdraw():
	reg = OfferRegistry()
	oid = reg.register((0,), "Avery")
	assert reg.accept(oid, "Blake") is True
	assert reg.reject(oid, "Blake") is True         # reject flips the earlier accept
	assert reg.get(oid).accepts == {"Avery"} and reg.get(oid).rejects == {"Blake"}
	assert reg.withdraw(oid) is True
	assert reg.accept(oid, "Casey") is False        # no votes on a dead offer
	assert reg.standing() == [] and oid not in reg.standing_ids()
	assert reg.accept("O99", "Avery") is False      # unknown id


def test_registry_apply_dispatch_and_json_round_trip():
	reg = OfferRegistry()
	assert reg.apply(Propose(deal=(2, 1)), "Avery", round=1) == "O1"
	assert reg.apply(Accept("O1"), "Blake") is None and reg.get("O1").accepts == {"Avery", "Blake"}
	assert reg.apply(Walk(), "Casey") is None       # walk touches nothing on the registry
	restored = OfferRegistry.from_json(reg.to_json())
	assert restored.get("O1").deal == (2, 1) and restored.get("O1").accepts == {"Avery", "Blake"}
	assert restored.register((0, 0), "Casey") == "O2"   # counter survived the round-trip


def test_offer_json_round_trip():
	o = Offer(offer_id="O1", deal=(0, 1), proposer="Avery", round=2, accepts={"Avery"})
	assert Offer.from_json(o.to_json()) == o


def test_action_from_json_inverts_to_json():
	for a in [Propose(deal=(0, 1, 2)), Accept("O1"), Reject("O2"), Walk()]:
		assert action_from_json(a.to_json()) == a
	# also reads a nested/aliased stored form
	assert action_from_json({"type": "accept", "id": "O3"}) == Accept("O3")


# ------------------------------------------------------------- parse_action ---

def test_parse_walk_and_accept_reject():
	assert parse_action(fence('{"action": "walk"}')).action == Walk()
	r = parse_action(fence('{"action": "accept", "offer_id": "O1"}'), standing={"O1"})
	assert r.ok and r.action == Accept("O1")
	# offer_id aliases
	assert parse_action(fence('{"action": "reject", "id": "O2"}')).action == Reject("O2")


def test_parse_syntax_failures():
	assert parse_action("no json at all").error_kind == SYNTAX
	assert parse_action(fence('{"deal": {}}')).error_kind == SYNTAX          # no "action"
	assert parse_action(fence('{"action": "frobnicate"}')).error_kind == SYNTAX
	assert parse_action(fence('{"action": "accept"}')).error_kind == SYNTAX  # accept without offer_id
	assert parse_action(fence('{"action": "propose"}')).error_kind == SYNTAX  # propose without deal


def test_parse_legality_failures():
	# accept an offer that isn't standing
	r = parse_action(fence('{"action": "accept", "offer_id": "O9"}'), standing={"O1"})
	assert not r.ok and r.error_kind == LEGALITY
	# a propose whose deal the decoder rejects (well-formed JSON, infeasible deal)
	r2 = parse_action(fence('{"action": "propose", "deal": {"Site": "nope"}}'),
	                  deal_decoder=lambda d: None)
	assert r2.error_kind == LEGALITY
	# an action kind disallowed at this decision point
	r3 = parse_action(fence('{"action": "propose", "deal": [0]}'), allowed={"accept", "reject"})
	assert r3.error_kind == LEGALITY


def test_parse_propose_with_and_without_decoder():
	# a decoder maps the model's issue object to a Deal tuple
	r = parse_action(fence('{"action": "propose", "deal": {"Site": "A", "Power": "B"}}'),
	                 deal_decoder=lambda d: (0, 1))
	assert r.ok and r.action == Propose(deal=(0, 1))
	# without a decoder, a plain index list is accepted; a dict cannot be decoded -> legality
	assert parse_action(fence('{"action": "propose", "deal": [0, 2, 1]}')).action == Propose(deal=(0, 2, 1))
	assert parse_action(fence('{"action": "propose", "deal": {"x": 1}}')).error_kind == LEGALITY


def test_parse_result_retry_directive():
	bad = ParseResult.bad(SYNTAX, "fix your JSON")
	assert bad.retry_directive() == {"retry": "fix your JSON", "error_kind": SYNTAX}
	assert ParseResult.good(Walk()).retry_directive() is None


def test_parse_action_accepts_nested_and_aliased_forms():
	# nested {"action": {"type": ...}} — the shape used when a move rides with cheap talk
	r = parse_action(fence('{"message": "final call", "action": {"type": "propose", "deal": [0, 1]}}'))
	assert r.ok and r.action == Propose(deal=(0, 1))
	# "move" alias for the action key, "kind" alias for the type
	assert parse_action(fence('{"move": {"kind": "walk"}}')).action == Walk()


# --------------------------------------------------------------- parse_turn ---

def test_parse_turn_separates_message_and_action():
	pt = parse_turn(fence('{"message": "I offer this", "action": {"type": "propose", "deal": [0, 2]}}'))
	assert isinstance(pt, ParsedTurn) and pt.ok
	assert pt.message == "I offer this" and pt.action == Propose(deal=(0, 2))
	assert pt.thinking is None            # <think> is stripped upstream, never reaches the public parse


def test_parse_turn_pure_cheap_talk_is_legal():
	pt = parse_turn(fence('{"message": "just talking, no move yet"}'))
	assert pt.ok and pt.action is None and pt.message == "just talking, no move yet"
	# ...unless an action is required at this phase
	pt2 = parse_turn(fence('{"message": "stalling"}'), require_action=True)
	assert not pt2.ok and pt2.error_kind == SYNTAX and pt2.message == "stalling"


def test_parse_turn_malformed_action_surfaces_error_and_retry():
	pt = parse_turn(fence('{"message": "hi", "action": {"type": "accept"}}'), standing={"O1"})
	assert not pt.ok and pt.error_kind == SYNTAX          # accept without offer_id
	assert pt.retry_directive() == {"retry": pt.error, "error_kind": SYNTAX}
	# legality: accept of a dead offer
	pt2 = parse_turn(fence('{"action": {"type": "accept", "offer_id": "O9"}}'), standing={"O1"})
	assert not pt2.ok and pt2.error_kind == LEGALITY
