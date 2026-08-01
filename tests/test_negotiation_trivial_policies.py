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

# [implement: rational_agents self-benefit — trivial-baselines lane] 2026-08-01
"""Tests for the three trivial decomposition policies — ``passive-gate`` / ``greedy-anchor`` /
``greedy-holdout`` — and the ``Pass`` action they need.

Two layers. The unit layer pins each policy's decision rule on hand-built ``NegotiationState``s, one case per
branch (ordinary turn, forced-final PROPOSAL turn where ``Reject`` is illegal, forced-final VOTE turn). The
integration layer seats each policy at seat 0 of a real ``ScorableNegotiation`` against scripted opponents and
asserts the property the campaign's validity gate depends on: a policy seat must produce **zero syntax and
zero legality errors** over a whole episode. That is not a formality — the phase-dependent legality of
``Reject``, and the duplicate-offer-id hazard of re-proposing a live deal, are both invisible at the unit level
and both silently corrupt a cell.
"""
from __future__ import annotations

import json

from interlens.arena.actions import Accept, Pass, Propose, Reject, Walk, action_from_json, action_message
from interlens.arena.negotiation.policy_participant import PolicyParticipant
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet
from interlens.arena.negotiation.space import DealSpace, Issue
from interlens.arena.negotiation.strategies import (BayesianRationalPolicy, DeclaredGreedyHoldoutPolicy,
                                                    DemandFractionPolicy, GreedyAnchorPolicy,
                                                    GreedyHoldoutPolicy, NegotiationState,
                                                    PassiveGatePolicy, ToughPolicy, ZOO)
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.arena.schema import Instance, PERSONAS, new_id
from interlens.arena.table import POLICY_FACTORIES, mixed_table
from interlens.message import Message
from interlens.participant.participant import Participant


# --------------------------------------------------------------------------------------------------------- #
# Fixtures: a one-issue game where seat 0's ranking is strict, so "own max" is unambiguous.
# --------------------------------------------------------------------------------------------------------- #
SPACE = DealSpace((Issue("I", ("X", "Y", "Z")),))
#: X=5 (surplus +2), Y=3 (surplus 0, still IR), Z=1 (surplus -2, below reservation).
SHEET0 = ScoreSheet("p0", ((5.0, 3.0, 1.0),), threshold=3.0)

BEST, IR_NOT_BEST, BELOW = (0,), (1,), (2,)


def state(deal=None, *, offer_id="P2", round=1, deadline=3, must_vote=False, my_offers=()):
    """A seat-0 state with ``deal`` standing (or nothing standing when ``deal`` is None)."""
    offers = {offer_id: tuple(deal)} if deal is not None else {}
    return NegotiationState(seat=0, sheet=SHEET0, space=SPACE, round=round, deadline=deadline,
                            offers=offers, standing=(offer_id if deal is not None else None),
                            received=([tuple(deal)] if deal is not None else []),
                            my_offers=[tuple(d) for d in my_offers], must_vote=must_vote, opponents=(1, 2))


def final_proposal_state(**kw):
    """The forced-final PROPOSAL turn: one round past the deadline with ``must_vote`` unset."""
    return state(round=4, deadline=3, **kw)


# --------------------------------------------------------------------------------------------------------- #
# The Pass action.
# --------------------------------------------------------------------------------------------------------- #
def test_pass_serializes_to_the_wire_tag_the_scenario_treats_as_a_clean_no_op():
    assert Pass().to_json() == {"action": "none"}
    assert action_from_json({"action": "none"}) == Pass()
    assert action_from_json({"action": "pass"}) == Pass()
    # the emitted envelope is exactly what ScorableNegotiation.apply short-circuits as a talk-only pass
    assert json.loads(action_message(Pass()).strip().removeprefix("```json").removesuffix("```")) == {
        "action": "none"}


def test_state_reports_the_forced_final_proposal_phase():
    assert final_proposal_state(deal=BELOW).final_proposal is True
    assert state(deal=BELOW).final_proposal is False                       # ordinary turn
    assert state(deal=BELOW, round=4, must_vote=True).final_proposal is False   # the VOTE half, not this one


# --------------------------------------------------------------------------------------------------------- #
# 1. passive-gate: pure discipline.
# --------------------------------------------------------------------------------------------------------- #
def test_passive_gate_accepts_ir_and_declines_below_and_never_proposes():
    pol = PassiveGatePolicy()
    assert pol(state(deal=BEST)) == Accept("P2")
    assert pol(state(deal=IR_NOT_BEST)) == Accept("P2")     # surplus exactly 0 is still individually rational
    assert pol(state(deal=BELOW)) == Reject("P2")
    assert pol(state(deal=None)) == Pass()                  # nothing to respond to -> stand pat, never open
    # exhaustive over every branch: this policy must never table a deal and never leave the table
    for st in (state(deal=d, round=r, must_vote=v, my_offers=m)
               for d in (None, BEST, IR_NOT_BEST, BELOW) for r in (1, 4) for v in (False, True)
               for m in ((), (BEST,))):
        assert not isinstance(pol(st), (Propose, Walk))


def test_passive_gate_declines_with_pass_not_reject_in_the_final_proposal_phase():
    """``Reject`` is an economic-legality violation on the forced-final proposal turn (allowed: propose /
    accept / walk), so the decline must downgrade to a pass or the cell accrues legality errors."""
    pol = PassiveGatePolicy()
    assert pol(final_proposal_state(deal=BELOW)) == Pass()
    assert pol(final_proposal_state(deal=BEST)) == Accept("P2")   # accepting IS legal here, and closes


def test_passive_gate_votes_the_same_rule():
    pol = PassiveGatePolicy()
    assert pol(state(deal=IR_NOT_BEST, must_vote=True)) == Accept("P2")
    assert pol(state(deal=BELOW, must_vote=True)) == Reject("P2")
    # and, unlike the base vote rule, it stands pat rather than WALKing when there is nothing to vote on
    assert pol(state(deal=None, must_vote=True)) == Pass()


# --------------------------------------------------------------------------------------------------------- #
# 2. greedy-anchor: maximally selfish proposals, individually-rational acceptance.
# --------------------------------------------------------------------------------------------------------- #
def test_greedy_anchor_tables_its_own_max_and_signs_anything_above_threshold():
    pol = GreedyAnchorPolicy()
    assert pol(state(deal=None)) == Propose(BEST)
    assert pol(state(deal=BELOW)) == Propose(BEST)          # decline by out-proposing, not by rejecting
    assert pol(state(deal=BEST)) == Accept("P2")
    assert pol(state(deal=IR_NOT_BEST)) == Accept("P2")     # signs a worse-than-max deal that still beats no-deal


def test_greedy_anchor_stands_pat_rather_than_minting_a_duplicate_offer_id():
    """The scenario never withdraws an offer, so re-proposing a live deal would split the opponents' ACCEPT
    votes across two ids for the same package and neither could reach unanimity."""
    pol = GreedyAnchorPolicy()
    assert pol(state(deal=BELOW, my_offers=(BEST,))) == Pass()
    # ... except on the forced-final proposal turn, where the opener's move IS the offer everyone votes on
    assert pol(final_proposal_state(deal=BELOW, my_offers=(BEST,))) == Propose(BEST)


def test_greedy_anchor_own_max_tie_break_is_canonical_and_deterministic():
    flat = ScoreSheet("p0", ((4.0, 4.0, 1.0),), threshold=0.0)   # X and Y tie at the top
    st = NegotiationState(seat=0, sheet=flat, space=SPACE, opponents=(1,))
    picks = {GreedyAnchorPolicy()(st) for _ in range(5)}
    assert picks == {Propose((0,))}                              # first deal in enumeration order, every time


# --------------------------------------------------------------------------------------------------------- #
# 3. greedy-holdout: take it or leave it.
# --------------------------------------------------------------------------------------------------------- #
def test_greedy_holdout_refuses_deals_it_would_profit_from():
    pol = GreedyHoldoutPolicy()
    assert pol(state(deal=BEST)) == Accept("P2")
    assert pol(state(deal=IR_NOT_BEST)) == Propose(BEST)         # IR, but not the max -> hold out
    assert pol(state(deal=IR_NOT_BEST, my_offers=(BEST,))) == Reject("P2")   # already tabled -> just decline
    assert pol(state(deal=None, my_offers=(BEST,))) == Pass()


def test_greedy_holdout_final_vote_refuses_the_last_round_logic_every_other_policy_applies():
    """On the terminal vote any ordinary rational agent accepts anything positive, because the only
    alternative is no-deal = 0. Refusing that is exactly what makes this policy the extraction upper bound."""
    ir_vote = state(deal=IR_NOT_BEST, must_vote=True)
    assert GreedyHoldoutPolicy()(ir_vote) == Reject("P2")
    for baseline in (PassiveGatePolicy(), GreedyAnchorPolicy(), ToughPolicy(), BayesianRationalPolicy()):
        assert baseline(ir_vote) == Accept("P2")
    assert GreedyHoldoutPolicy()(state(deal=BEST, must_vote=True)) == Accept("P2")
    assert isinstance(GreedyHoldoutPolicy()(state(deal=None, must_vote=True)), Walk)   # degenerate, base rule


def test_greedy_holdout_declines_with_pass_in_the_final_proposal_phase():
    pol = GreedyHoldoutPolicy()
    assert pol(final_proposal_state(deal=IR_NOT_BEST, my_offers=(BEST,))) == Propose(BEST)


# --------------------------------------------------------------------------------------------------------- #
# 4. Registration: the policies are reachable by the names the CLI takes.
# --------------------------------------------------------------------------------------------------------- #
def test_trivial_policies_are_registered_under_their_cli_names():
    for name, cls in (("passive-gate", PassiveGatePolicy), ("greedy-anchor", GreedyAnchorPolicy),
                      ("greedy-holdout", GreedyHoldoutPolicy),
                      ("greedy-holdout-declared", DeclaredGreedyHoldoutPolicy),
                      ("demand-90-declared", DemandFractionPolicy)):
        assert isinstance(ZOO[name](), cls)
        assert isinstance(POLICY_FACTORIES[name](), cls)
        assert POLICY_FACTORIES[name]().name == name


def test_policies_do_not_bleed_utilities_across_seats():
    """One policy instance may serve several seats (and concurrent episodes); its cached own-utility column is
    keyed by seat, so seat 1's max must not leak into seat 0's decision."""
    sheet1 = ScoreSheet("p1", ((1.0, 3.0, 5.0),), threshold=0.0)    # mirror image: Z is p1's max
    for pol in (GreedyAnchorPolicy(), GreedyHoldoutPolicy()):
        st0 = NegotiationState(seat=0, sheet=SHEET0, space=SPACE, opponents=(1,))
        st1 = NegotiationState(seat=1, sheet=sheet1, space=SPACE, opponents=(0,))
        assert pol(st0) == Propose((0,)) and pol(st1) == Propose((2,))
        assert pol(st0) == Propose((0,))                            # and back again, order-independent


# --------------------------------------------------------------------------------------------------------- #
# 4b. Declared-commitment variants: same behaviour, announced once.
# --------------------------------------------------------------------------------------------------------- #
def test_declared_holdout_behaves_identically_to_the_silent_holdout():
    """The declaration must be the ONLY difference, or the paired contrast measures two things at once."""
    silent, declared = GreedyHoldoutPolicy(), DeclaredGreedyHoldoutPolicy()
    for st in (state(deal=d, round=r, must_vote=v, my_offers=m)
               for d in (None, BEST, IR_NOT_BEST, BELOW) for r in (1, 4) for v in (False, True)
               for m in ((), (BEST,))):
        assert silent(st) == declared(st)


def test_declared_holdout_names_the_only_package_it_will_take():
    text = DeclaredGreedyHoldoutPolicy().declaration(state(deal=None))
    assert "I: X" in text                       # the own-max deal, rendered as issue: option
    assert "final vote" in text                 # states that the rule survives the terminal round


def test_demand_fraction_accepts_at_the_bar_and_declines_below_it():
    """The bar is a fraction of the own MAXIMUM score, not of the reservation value."""
    #  X=5 (max), Y=3, Z=1; threshold 3. At accept_frac 0.5 the bar is max(2.5, 3.0) = 3.0, so Y qualifies.
    half = DemandFractionPolicy(accept_frac=0.5)
    assert half(state(deal=IR_NOT_BEST)) == Accept("P2")
    assert half(state(deal=BELOW, my_offers=(BEST,))) == Reject("P2")
    #  At 0.9 the bar is 4.5, so only X qualifies and the individually-rational Y is declined.
    strict = DemandFractionPolicy(accept_frac=0.9)
    assert strict(state(deal=BEST)) == Accept("P2")
    assert strict(state(deal=IR_NOT_BEST, my_offers=(BEST,))) == Reject("P2")
    assert strict(state(deal=IR_NOT_BEST)) == Propose(BEST)


def test_demand_fraction_bar_never_drops_below_the_reservation_value():
    """A low fraction must not licence signing a deal worse than no deal (an IR violation)."""
    lax = DemandFractionPolicy(accept_frac=0.01)
    assert lax._bar(state()) == 3.0                       # the threshold, not 0.05
    assert lax(state(deal=BELOW, my_offers=(BEST,))) == Reject("P2")
    assert lax(state(deal=BELOW, must_vote=True)) == Reject("P2")


def test_demand_fraction_declares_the_numeric_bar_it_will_honour():
    pol = DemandFractionPolicy(accept_frac=0.9)
    text = pol.declaration(state(deal=None))
    assert "4.5" in text                                  # 0.9 x own max of 5.0, its own private information
    assert pol.name == "demand-90-declared"


def test_declaration_is_published_once_and_only_on_the_first_turn():
    """End to end through the participant: the declaration rides in the envelope's `message` key (which a
    chat-enabled scenario republishes), and the view — not participant memory — is what makes it one-shot."""
    game = _game()
    part = PolicyParticipant("p0", DeclaredGreedyHoldoutPolicy(), seat=0, sheet=game.sheets[0],
                             space=game.space, deadline=2, n_seats=3)
    opening = part.generate([{"role": "user", "content": "your move"}], seat="Alpha")
    payload = json.loads(opening.content.strip().removeprefix("```json").removesuffix("```"))
    assert "I will only ever accept" in payload["message"]
    assert payload["action"] == "propose"                 # the formal move rides along unchanged
    assert "I will only ever accept" in opening.metadata["message"]
    # a later turn, with this seat's own opening now in the view, carries no message at all
    later = part.generate([{"role": "user", "content": "your move"},
                           {"role": "assistant", "content": opening.content},
                           {"role": "user", "content": "your move"}], seat="Alpha")
    assert "message" not in json.loads(later.content.strip().removeprefix("```json").removesuffix("```"))
    assert "message" not in later.metadata


def test_silent_policies_emit_no_message_key_at_all():
    game = _game()
    for policy in (PassiveGatePolicy(), GreedyAnchorPolicy(), GreedyHoldoutPolicy(), ToughPolicy()):
        part = PolicyParticipant("p0", policy, seat=0, sheet=game.sheets[0], space=game.space,
                                 deadline=2, n_seats=3)
        msg = part.generate([{"role": "user", "content": "your move"}], seat="Alpha")
        assert "message" not in json.loads(msg.content.strip().removeprefix("```json").removesuffix("```"))


def test_declaration_reaches_the_other_seats_public_view():
    """The point of a declaration is that the OPPONENTS read it, so assert on the scenario's event log."""
    st = _drive("greedy-holdout-declared", rounds=2)
    said = [e for e in st["events"] if e["seat"] == PERSONAS[0] and "I will only ever accept" in e["content"]]
    assert len(said) == 1, f"declaration appeared {len(said)} times in the public log"


# --------------------------------------------------------------------------------------------------------- #
# 5. Integration: a policy seat in a real episode must never accrue a syntax or legality error.
# --------------------------------------------------------------------------------------------------------- #
def _game(rounds: int = 2) -> GameSpec:
    space = DealSpace((Issue("Site", ("North", "South")), Issue("Fund", ("Low", "Mid", "High"))))
    sheets = (
        ScoreSheet("Alpha", ((10.0, 0.0), (0.0, 3.0, 6.0)), threshold=5.0),
        ScoreSheet("Beta", ((0.0, 10.0), (0.0, 3.0, 6.0)), threshold=0.0),
        ScoreSheet("Gamma", ((5.0, 5.0), (6.0, 3.0, 0.0)), threshold=0.0),
    )
    return GameSpec(space, sheets, rounds=rounds, info="full", chat=True, proposer=0, min_accept=None)


class Agreeable(Participant):
    """A scripted stand-in for an agreeable LLM seat: accept whatever is standing, else table a fixed package.
    Reads the authoritative ``negotiation_state`` block, so it needs no English parsing."""

    self_role, others_role = "assistant", "user"

    def __init__(self, opener: dict):
        self.name = "agreeable"
        self.opener = opener
        self.system_prompt = None
        self.private_context = ()

    def generate(self, view, *, seat: str | None = None, **kwargs) -> Message:
        from interlens.arena.negotiation.strategies import parse_negotiation_state
        block = next((b for b in (parse_negotiation_state(seg.get("content", "")) for seg in reversed(view))
                      if b is not None), None)
        standing = (block or {}).get("standing")
        obj = ({"message": "fine by me.", "action": "accept", "offer_id": standing} if standing else
               {"message": "here is a package.", "action": "propose", "deal": self.opener})
        return Message(self.name, "```json\n" + json.dumps(obj) + "\n```")


def _drive(policy_name: str, rounds: int = 2) -> dict:
    """Step the scenario to completion with ``policy_name`` at seat 0 and agreeable scripted seats elsewhere,
    returning the finished state (so the test can read the error counters and the offer registry)."""
    game = _game(rounds)
    inst = Instance(new_id("trivial-test"), ScorableNegotiation.name, 0, 0,
                    payload=game.to_json(), ceiling=1.0, floor=0.0, solution={})
    agreeable = Agreeable({"Site": "South", "Fund": "Mid"})
    table = mixed_table(game, {i: agreeable for i in (1, 2)}, deadline=rounds, full_info=True,
                        fill_policy=policy_name)
    scen = ScorableNegotiation()
    st = scen.make_state(inst, "moves_chat", seed=0)
    for _guard in range(400):
        if st["done"]:
            break
        reqs = scen.next_requests(st)
        if not reqs:
            break
        for req in reqs:
            directive = scen.apply(st, req, table.generate(req.view, seat=req.seat).content)
            assert directive is None or "retry" not in directive, (
                f"{policy_name} seat forced a retry: {directive}")
    return st


def test_every_trivial_policy_plays_a_clean_episode():
    for name in ("passive-gate", "greedy-anchor", "greedy-holdout", "greedy-holdout-declared",
                 "demand-90-declared"):
        st = _drive(name)
        assert st["done"], f"{name} episode never terminated"
        assert st["syntax_errors"] == 0, f"{name} produced syntax errors"
        assert st["legality_errors"] == 0, f"{name} produced legality errors"
        assert st["economic_errors"] == 0, f"{name} signed or tabled a below-threshold deal"


def test_greedy_policies_table_their_deal_exactly_once():
    """The duplicate-offer-id hazard, checked on the ledger rather than on the decision rule."""
    for name in ("greedy-anchor", "greedy-holdout", "greedy-holdout-declared", "demand-90-declared"):
        st = _drive(name, rounds=4)
        seat0 = PERSONAS[0]
        mine = [o for o in st["registry"].offers.values() if o.proposer == seat0]
        assert len({o.deal for o in mine}) <= 1, f"{name} tabled more than one distinct deal"
        assert len(mine) <= 1, f"{name} minted {len(mine)} offer ids for one package"


def test_passive_gate_never_appears_in_the_offer_ledger():
    st = _drive("passive-gate", rounds=4)
    assert not [o for o in st["registry"].offers.values() if o.proposer == PERSONAS[0]]


def test_greedy_holdout_blocks_a_deal_it_would_have_profited_from():
    """The agreeable seats table a package that clears seat 0's threshold; ``greedy-anchor`` signs it (or wins
    its own), ``greedy-holdout`` refuses everything but its own max — the extraction/closure trade-off the
    experiment is measuring."""
    holdout = _drive("greedy-holdout", rounds=2)
    anchor = _drive("greedy-anchor", rounds=2)
    assert anchor["final_deal"] is not None
    if holdout["final_deal"] is not None:
        # closure is only possible on the holdout's own maximum
        best = GreedyHoldoutPolicy()._own_max_deal(
            NegotiationState(seat=0, sheet=_game().sheets[0], space=_game().space, opponents=(1, 2)))
        assert tuple(holdout["final_deal"]) == best
