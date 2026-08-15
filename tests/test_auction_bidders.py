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

"""The computable bidders: the preregistered G3 rational-equals-oracle property, winner's-curse conditioning,
stage myopia, the oracle's Dutch edge, and the templated DM decision rules (design.md §4.1, §3.4, §6 G3)."""
from __future__ import annotations

import numpy as np
import pytest

from interlens.arena.auction import bidders as P
from interlens.arena.auction.actions import Bid, Claim, Exit, PassLot, SAATurn, Stay, Wait
from interlens.arena.auction.spec import Mechanism, generate_spec


def _states(spec, t, *, information="private"):
    return [P.AuctionState.from_spec(spec, t, i, information=information) for i in range(spec.n_bidders)]


# --------------------------------------------------------------------------- G3 ---
@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_g3_rational_and_oracle_bid_identically_in_second_price_ipv(seed):
    """design.md G3: in a second-price IPV stage the rational and oracle seats must bid exactly their own
    value in EVERY stage of EVERY episode. Any deviation is a bug, not a finding."""
    spec = generate_spec(seed, mechanism=Mechanism.sealed(), value_structure="ipv", horizon=4)
    rational, oracle = P.ConditionalBayesPolicy("private"), P.ConditionalBayesPolicy("oracle")
    for t in range(1, spec.horizon + 1):
        for seat in range(spec.n_bidders):
            priv = P.AuctionState.from_spec(spec, t, seat)
            omni = P.AuctionState.from_spec(spec, t, seat, information="oracle")
            a, b = rational.act(priv), oracle.act(omni)
            assert a == b
            assert a.amount == min(int(spec.stage(t).values[seat][0]), int(spec.stage(t).budgets[seat]))


def test_truthful_policy_is_the_same_function_under_both_information_arms():
    spec = generate_spec(3, mechanism=Mechanism.sealed(), value_structure="apv", horizon=2)
    t_priv, t_oracle = P.TruthfulPolicy("private"), P.TruthfulPolicy("oracle")
    for seat in range(spec.n_bidders):
        priv = P.AuctionState.from_spec(spec, 1, seat)
        omni = P.AuctionState.from_spec(spec, 1, seat, information="oracle")
        assert t_priv.bid_for(priv, 0) == t_oracle.bid_for(omni, 0) == int(spec.stage(1).values[seat][0])


def test_stage_myopia_the_bid_depends_only_on_this_stage():
    """G3's repeated-tier extension: the rational seat's stage-t bid is independent of stages 1..t-1 given
    stage-t values. Reordering the episode's stages must not change any stage's bid."""
    import dataclasses

    spec = generate_spec(21, mechanism=Mechanism.sealed(), value_structure="apv", horizon=4)
    pol = P.ConditionalBayesPolicy("private")
    per_stage = {t: [pol.act(s).amount for s in _states(spec, t)] for t in range(1, 5)}
    # Rebuild the same stages in reverse order and re-price them; each stage keeps its own bids.
    reversed_stages = tuple(dataclasses.replace(s, stage=i + 1)
                            for i, s in enumerate(reversed(spec.stages)))
    rev = dataclasses.replace(spec, stages=reversed_stages)
    for t in range(1, 5):
        assert [pol.act(s).amount for s in _states(rev, t)] == per_stage[spec.horizon + 1 - t]


# ------------------------------------------------------------- winner's curse ---
def test_conditional_bayes_shades_below_the_naive_value_under_common_values():
    spec = generate_spec(4, mechanism=Mechanism.sealed(), value_structure="interdep", horizon=2)
    seat = next(i for i, g in enumerate(spec.gammas) if g > 0)
    state = P.AuctionState.from_spec(spec, 1, seat)
    naive = float(state.values[0]) + spec.gammas[seat] * float(state.signals[0])
    pol = P.ConditionalBayesPolicy("private")
    assert pol.bid_for(state, 0) < naive
    # And the correction is the only thing separating it from the private-values case.
    assert pol.bid_for(state, 0) > float(state.values[0])


def test_no_curse_correction_without_a_resale_weight():
    spec = generate_spec(4, mechanism=Mechanism.sealed(), value_structure="interdep", horizon=2)
    seat = next(i for i, g in enumerate(spec.gammas) if g == 0)
    state = P.AuctionState.from_spec(spec, 1, seat)
    assert P.ConditionalBayesPolicy("private").bid_for(state, 0) == int(state.values[0])


# ----------------------------------------------------------- format behaviour ---
def test_oracle_claims_just_above_the_second_highest_value_in_dutch_and_sits_out_when_it_cannot_win():
    spec = generate_spec(4, mechanism=Mechanism.dutch(), value_structure="apv", horizon=1)
    values = [v[0] for v in spec.stage(1).values]
    top = int(np.argmax(values))
    second = sorted(values)[-2]
    pol = P.RNNEPolicy("oracle")
    winner_state = P.AuctionState.from_spec(spec, 1, top, information="oracle")
    assert pol.bid_for(winner_state, 0) == min(values[top], second + 1)
    loser = next(i for i in range(spec.n_bidders) if i != top)
    loser_state = P.AuctionState.from_spec(spec, 1, loser, information="oracle")
    assert pol.bid_for(loser_state, 0) == spec.mechanism.reserve


def test_rational_dutch_bid_stays_below_own_value():
    spec = generate_spec(8, mechanism=Mechanism.dutch(), value_structure="apv", horizon=1)
    pol = P.ConditionalBayesPolicy("private")
    for seat, state in enumerate(_states(spec, 1)):
        assert pol.bid_for(state, 0) <= int(state.values[0])


def test_clock_moves_are_typed_and_price_driven():
    spec = generate_spec(8, mechanism=Mechanism.english(), value_structure="apv", horizon=1)
    pol = P.ConditionalBayesPolicy("private")
    state = P.AuctionState.from_spec(spec, 1, 0)
    state.clock_price = int(state.values[0]) - 1
    assert isinstance(pol.act(state), Stay)
    state.clock_price = int(state.values[0]) + 1
    assert isinstance(pol.act(state), Exit)
    dspec = generate_spec(8, mechanism=Mechanism.dutch(), value_structure="ipv", horizon=1)
    dstate = P.AuctionState.from_spec(dspec, 1, 0)
    dstate.clock_price = 10 ** 6
    assert isinstance(pol.act(dstate), Wait)
    dstate.clock_price = 0
    assert isinstance(pol.act(dstate), Claim)


def test_saa_move_is_straightforward_and_respects_the_ratchet_shape():
    spec = generate_spec(6, mechanism=Mechanism.saa(4), value_structure="apv", horizon=1)
    pol = P.ConditionalBayesPolicy("private")
    state = P.AuctionState.from_spec(spec, 1, 0)
    move = pol.act(state)
    # An SAA turn is a SET of moves, not one: the demand correspondence is a bundle argmax, so the policy
    # decides the whole round at once rather than one lot at a time.
    assert isinstance(move, SAATurn)
    assert not (move.bids and move.passes)
    for bid in move.bids:
        assert bid.amount == spec.mechanism.reserve + spec.mechanism.increment
    assert len({b.item for b in move.bids}) == len(move.bids)
    assert len(move.bids) <= int(spec.capacities[0])


def test_saa_policy_demand_is_the_benchmark_rule_itself():
    """G3's precondition: the played rule and the rule ``bid_benchmark_ratio`` scores it against are ONE rule.

    A greedy lot-at-a-time derivation passes at 3 lots — where taking the best lot and re-solving happens to
    reach the bundle argmax — and silently diverges once synergies make a lot's marginal value depend on the
    rest of the bundle, which is why this asserts against ``best_bundle_at_prices`` at a lot count where the
    two can come apart rather than at the smallest one."""
    from interlens.arena.auction.benchmarks import best_bundle_at_prices

    for seed in (6, 11, 23, 84001):
        spec = generate_spec(seed, mechanism=Mechanism.saa(10), value_structure="apv", horizon=1)
        for seat in range(spec.n_bidders):
            state = P.AuctionState.from_spec(spec, 1, seat)
            move = pol_act = P.ConditionalBayesPolicy("private").act(state)
            assert isinstance(pol_act, SAATurn)
            vm = state.value_model()
            pay = np.full(spec.n_items, float(spec.mechanism.reserve + spec.mechanism.increment))
            bundle, surplus = best_bundle_at_prices(vm, 0, pay, forced=())
            if surplus <= 0:
                assert not move.bids
                continue
            # Equal up to the lots the budget forces the seat to drop, which the benchmark does not model;
            # nothing outside the argmax bundle may ever be bid on.
            assert {b.item for b in move.bids} <= set(bundle)


def test_demand_schedule_shades_under_uniform_pricing_and_not_under_clinching():
    uni = generate_spec(6, mechanism=Mechanism.uniform_price(3), value_structure="apv", horizon=1)
    cli = generate_spec(6, mechanism=Mechanism.clinching(3), value_structure="apv", horizon=1)
    pol = P.DemandSchedulePolicy("private")
    truthful = P.AuctionPolicy.schedule(pol, P.AuctionState.from_spec(cli, 1, 0))
    assert pol.schedule(P.AuctionState.from_spec(cli, 1, 0)) == truthful
    shaded = pol.schedule(P.AuctionState.from_spec(uni, 1, 0))
    assert shaded[0] == truthful[0]                       # the marginal unit is never shaded
    assert all(a <= b for a, b in zip(shaded, truthful))
    assert all(shaded[k] >= shaded[k + 1] for k in range(len(shaded) - 1))    # weakly decreasing


# ------------------------------------------------------- the templated channel ---
def test_a_price_proposal_below_the_best_response_is_declined_with_its_arithmetic():
    spec = generate_spec(4, mechanism=Mechanism.sealed(), value_structure="apv", horizon=1)
    pol = P.ConditionalBayesPolicy("private")
    state = P.AuctionState.from_spec(spec, 1, 0)
    br = pol.bid_for(state, 0)
    low = pol.evaluate_proposal(state, P.Proposal(proposer=1, item=0, price=int(br * 0.5)))
    assert not low.accept and low.reason == "dominated_by_best_response"
    assert low.detail["proposal_surplus"] < low.detail["best_response_surplus"]
    assert "Declining" in low.sentence()
    same = pol.evaluate_proposal(state, P.Proposal(proposer=1, item=0, price=br))
    assert same.accept and same.reason == "matches_best_response"


def test_a_proposal_above_own_value_is_declined_as_below_reservation():
    spec = generate_spec(4, mechanism=Mechanism.sealed(), value_structure="apv", horizon=1)
    state = P.AuctionState.from_spec(spec, 1, 0)
    d = P.ConditionalBayesPolicy().evaluate_proposal(
        state, P.Proposal(proposer=1, item=0, price=int(state.values[0]) + 50))
    assert not d.accept and d.reason == "below_reservation"


def test_a_division_beyond_capacity_is_declined_on_capacity_grounds():
    spec = generate_spec(6, mechanism=Mechanism.saa(4), value_structure="apv", horizon=1)
    state = P.AuctionState.from_spec(spec, 1, 0)
    too_many = tuple(range(spec.capacities[0] + 1))
    d = P.ConditionalBayesPolicy().evaluate_proposal(
        state, P.Proposal(proposer=1, assignment={0: too_many}))
    assert not d.accept and d.reason == "exceeds_capacity"


def test_a_policy_seat_speaks_and_initiates_without_leaking_private_numbers():
    spec = generate_spec(6, mechanism=Mechanism.saa(4), value_structure="apv", horizon=1)
    state = P.AuctionState.from_spec(spec, 1, 0)
    pol = P.ConditionalBayesPolicy("private")
    said = pol.declaration(state)
    private_numbers = {str(int(v)) for v in state.values} | {str(int(state.budget))}
    assert said and not any(n in said for n in private_numbers if len(n) > 2)
    proposal = pol.initiate_proposal(state)
    assert proposal is None or (proposal.proposer == 0 and proposal.assignment is not None)
    decision, sentence = pol.respond_to_dm(state, P.Proposal(proposer=1, item=0, price=1))
    assert isinstance(sentence, str) and decision.reason


def test_a_private_information_policy_never_reads_rival_values():
    spec = generate_spec(4, mechanism=Mechanism.dutch(), value_structure="apv", horizon=1)
    pol = P.ConditionalBayesPolicy("private")
    # Even handed an oracle-populated state, a private-information policy refuses the extra information.
    state = P.AuctionState.from_spec(spec, 1, 0, information="oracle")
    assert pol._rival_values(state, 0) is None
    assert pol.bid_for(state, 0) == pol.bid_for(P.AuctionState.from_spec(spec, 1, 0), 0)


def test_policy_for_dispatches_by_family_and_rejects_a_bad_information_arm():
    uni = generate_spec(1, mechanism=Mechanism.uniform_price(3), horizon=1)
    sealed = generate_spec(1, mechanism=Mechanism.sealed(), horizon=1)
    assert isinstance(P.policy_for(uni), P.DemandSchedulePolicy)
    assert isinstance(P.policy_for(sealed, information="oracle"), P.ConditionalBayesPolicy)
    assert P.policy_for(sealed, information="oracle").is_oracle
    with pytest.raises(ValueError):
        P.TruthfulPolicy("omniscient")
    assert set(P.AUCTION_POLICIES) == {"truthful", "rnne", "conditional_bayes", "demand_schedule"}
