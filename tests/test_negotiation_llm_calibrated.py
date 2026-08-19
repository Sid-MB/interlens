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

# [implement f: fixing rational — fix-direction (B)] 2026-08-18
"""Tests for :mod:`interlens.arena.negotiation.llm_calibrated`.

Four layers.

1. **Offer-curve arithmetic**: bins resolve, pmfs normalize, schema validation rejects malformed fits.
2. **The step-equivalence regression (load-bearing)**: with step acceptance curves and no offer model, the
   policy's acceptance TABLE and its ACTION are byte-identical to ``BayesianRationalPolicy`` on
   private-information states with real offer histories. The design claim is "same machinery, opponent model
   swapped"; if this breaks, every Bayes-vs-calibrated contrast is confounded.
3. **Property tests**: affine invariance of the decision (the program's hard constraint), IR safety (never
   accepts below own threshold, on ordinary turns and the terminal vote), replay determinism.
4. **Direction**: an accepting opponent model plus a thin empirical offer stream must lower the reservation
   relative to the Bayesian one — the mechanism the closure intervention rests on.
"""
from __future__ import annotations

import numpy as np
import pytest

from interlens.arena.negotiation.calibrated import AcceptanceCurve, AcceptanceCurveSet
from interlens.arena.negotiation.generate import generate_game
from interlens.arena.negotiation.llm_calibrated import (LLMCalibratedRationalPolicy, LLMOpponentModel,
                                                        OfferCurve, OfferCurveSet)
from interlens.arena.negotiation.oracle_context import Accept, Propose, Walk
from interlens.arena.negotiation.strategies import BayesianRationalPolicy, NegotiationState

MODEL = "claude-opus-5"


# ------------------------------------------------------------------------------- fixtures --
def _game(seed: int = 0):
    game, _ = generate_game(n_parties=3, n_issues=3, n_options=3, rounds=6, info="private", seed=seed)
    return game


def _state(game, *, seat: int = 0, rnd: int = 1, deadline: int = 6, offers=None, standing=None,
           received_by_opponent=None, my_offers=(), offer_proposers=None) -> NegotiationState:
    """A PRIVATE-information state (``tables=None`` — the regime this policy exists for)."""
    offers = dict(offers or {})
    rbo = {k: [tuple(d) for d in v] for k, v in (received_by_opponent or {}).items()}
    received = [d for deals in rbo.values() for d in deals]
    return NegotiationState(
        seat=seat, sheet=game.sheets[seat], space=game.space, round=rnd, deadline=deadline,
        offers=offers, standing=standing, received=received, received_by_opponent=rbo,
        my_offers=[tuple(d) for d in my_offers], discount=float(game.discount), tables=None,
        opponents=tuple(i for i in range(game.n_parties) if i != seat),
        offer_proposers=dict(offer_proposers or {}))


def _mid_game_state(game, *, seat: int = 0, rnd: int = 3, deadline: int = 6):
    """A state with a real offer history: each opponent has proposed twice (its own best deal then a slight
    concession), and the latest opponent offer is standing. This is the shape every real mid-game turn has,
    so the equivalence and property tests run on the path that matters rather than on empty openings."""
    from interlens.arena.negotiation.oracle_context import deal_list
    deals = deal_list(game.space)
    offers, rbo, proposers = {}, {}, {}
    k = 1
    for opp in range(game.n_parties):
        if opp == seat:
            continue
        u = np.array([game.sheets[opp].utility(d) for d in deals])
        order = np.argsort(-u)
        seq = [tuple(int(x) for x in deals[order[0]]), tuple(int(x) for x in deals[order[3]])]
        rbo[opp] = seq
        for d in seq:
            oid = f"P{k}"
            offers[oid] = d
            proposers[oid] = opp
            k += 1
    return _state(game, seat=seat, rnd=rnd, deadline=deadline, offers=offers, standing=f"P{k-1}",
                  received_by_opponent=rbo, my_offers=[], offer_proposers=proposers)


def _soft_curves(b: float = 4.0) -> AcceptanceCurveSet:
    """A fitted-shaped acceptance set: opponents accept below threshold sometimes, good deals often."""
    return AcceptanceCurveSet(z_space="surplus_norm",
                              curves={MODEL: AcceptanceCurve(form="logistic_rounds",
                                                             params={"a": -0.5, "b": b, "c": -0.1})})


def _offer_curves(levels=((0.05, 0.15, 0.30), (0.10, 0.25, 0.45))) -> OfferCurveSet:
    return OfferCurveSet(curves={MODEL: OfferCurve(frac_edges=(0.5,), z_quantiles=levels)})


def _model(acceptance=None, offers=None, vote=None) -> LLMOpponentModel:
    return LLMOpponentModel(acceptance=acceptance or _soft_curves(), acceptance_vote=vote, offers=offers)


# --------------------------------------------------------------------------- offer-curve arithmetic --
def test_offer_curve_pmf_selects_round_bin_and_normalizes():
    c = OfferCurve(frac_edges=(0.5,), z_quantiles=((0.1, 0.2), (0.3, 0.4, 0.5)))
    early_v, early_p = c.pmf(0.0)
    late_v, late_p = c.pmf(0.9)
    assert early_v.tolist() == [0.1, 0.2] and early_p.sum() == pytest.approx(1.0)
    assert late_v.tolist() == [0.3, 0.4, 0.5] and late_p.sum() == pytest.approx(1.0)
    assert c.pmf(1.5)[0].tolist() == [0.3, 0.4, 0.5]      # fraction clipped into [0, 1]


def test_offer_curve_rejects_malformed_fits():
    with pytest.raises(ValueError):
        OfferCurve(frac_edges=(0.5, 0.4), z_quantiles=((0.1,), (0.2,), (0.3,)))
    with pytest.raises(ValueError):
        OfferCurve(frac_edges=(0.5,), z_quantiles=((0.1,),))          # wrong row count
    with pytest.raises(ValueError):
        OfferCurve(frac_edges=(), z_quantiles=((),))                  # empty support


def test_offer_curve_set_unknown_model_is_an_error():
    with pytest.raises(KeyError):
        _offer_curves().for_model("nobody-fit-this")


def test_unfitted_opponent_fails_at_construction():
    with pytest.raises(KeyError):
        LLMCalibratedRationalPolicy(model=_model(), opponent_model="nobody-fit-this")


# --------------------------------------------------------------------------- step equivalence --
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_step_curves_reproduce_bayesian_acceptance_table(seed):
    game = _game(seed)
    state = _mid_game_state(game)
    bayes = BayesianRationalPolicy()
    calib = LLMCalibratedRationalPolicy(model=LLMOpponentModel.step(), opponent_model=MODEL)
    tb, tc = bayes._tables(state), calib._tables(state)
    np.testing.assert_array_equal(calib._accept_prob_table(state, tc), bayes._accept_prob_table(state, tb))


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
@pytest.mark.parametrize("rnd", [1, 3, 6])
def test_step_model_actions_identical_to_bayesian(seed, rnd):
    game = _game(seed)
    state = _mid_game_state(game, rnd=rnd)
    bayes = BayesianRationalPolicy()
    calib = LLMCalibratedRationalPolicy(model=LLMOpponentModel.step(), opponent_model=MODEL)
    assert calib(state).to_json() == bayes(state).to_json()
    vote_state = _mid_game_state(game, rnd=game.rounds + 1)
    vote_state.must_vote = True
    assert calib(vote_state).to_json() == bayes(vote_state).to_json()


# --------------------------------------------------------------------------- property tests --
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_affine_invariance_of_the_decision(seed):
    """Rescale this seat's private sheet by a positive affine map: every decision must be unchanged —
    the fitted model lives in z space and the recursion in own-surplus units, both of which transform
    linearly, so the argmax/threshold comparisons cannot move."""
    game = _game(seed)
    policy = LLMCalibratedRationalPolicy(model=_model(offers=_offer_curves()), opponent_model=MODEL)
    state = _mid_game_state(game)
    base = policy(state).to_json()
    scaled_sheet = game.sheets[state.seat].rescaled(3.7, 11.0)
    scaled = _mid_game_state(game)
    scaled.sheet = scaled_sheet
    policy2 = LLMCalibratedRationalPolicy(model=_model(offers=_offer_curves()), opponent_model=MODEL)
    assert policy2(scaled).to_json() == base


@pytest.mark.parametrize("seed", range(6))
def test_ir_safety_never_accepts_below_own_threshold(seed):
    """Force the standing offer to be the seat's own WORST deal (strictly below threshold in these games) with
    a maximally accepting opponent model: the policy must still refuse, on ordinary turns and the vote."""
    game = _game(seed)
    from interlens.arena.negotiation.oracle_context import deal_list
    deals = deal_list(game.space)
    u = np.array([game.sheets[0].utility(d) for d in deals])
    worst = tuple(int(x) for x in deals[int(np.argmin(u))])
    if game.sheets[0].surplus(worst) >= 0:
        pytest.skip("degenerate game: even the worst deal clears the threshold")
    eager = AcceptanceCurveSet(z_space="surplus_norm",
                               curves={MODEL: AcceptanceCurve(form="logistic", params={"a": 10.0, "b": 0.0})})
    policy = LLMCalibratedRationalPolicy(model=_model(acceptance=eager, offers=_offer_curves()),
                                         opponent_model=MODEL)
    state = _mid_game_state(game)
    state.offers["BAD"] = worst
    state.standing = "BAD"
    state.offer_proposers["BAD"] = 1
    action = policy(state)
    assert not (isinstance(action, Accept) and action.offer_id == "BAD")
    state.must_vote = True
    vote = policy(state)
    assert not isinstance(vote, Accept)


@pytest.mark.parametrize("seed", [0, 1])
def test_replay_determinism(seed):
    game = _game(seed)
    make = lambda: LLMCalibratedRationalPolicy(model=_model(offers=_offer_curves()), opponent_model=MODEL)
    a = [make()(_mid_game_state(game, rnd=r)).to_json() for r in (1, 2, 4, 6)]
    b = [make()(_mid_game_state(game, rnd=r)).to_json() for r in (1, 2, 4, 6)]
    assert a == b


def test_policy_seat_models_keep_the_bayesian_column():
    """A computable opponent (seat model 'policy:*') keeps the parent's step-posterior column even when the
    LLM columns are calibrated — the fitted curves describe LLMs, not the project's own agents."""
    game = _game(0)
    state = _mid_game_state(game)
    bayes = BayesianRationalPolicy()
    calib = LLMCalibratedRationalPolicy(model=_model(), opponent_model=MODEL,
                                        seat_models={1: "policy:bayes-rational"})
    ap_b = bayes._accept_prob_table(state, bayes._tables(state))
    ap_c = calib._accept_prob_table(state, calib._tables(state))
    np.testing.assert_array_equal(ap_c[:, 1], ap_b[:, 1])
    assert not np.array_equal(ap_c[:, 2], ap_b[:, 2])     # the LLM column really did change


def test_vote_grain_switch_applies_only_in_the_endgame():
    game = _game(0)
    vote = AcceptanceCurveSet(z_space="surplus_norm",
                              curves={MODEL: AcceptanceCurve(form="bins",
                                                             params={"z_edges": [0.0], "p": [0.8, 0.99]})})
    policy = LLMCalibratedRationalPolicy(model=_model(vote=vote), opponent_model=MODEL, endgame_rounds=1)
    early = _mid_game_state(game, rnd=1)
    policy._accept_prob_table(early, policy._tables(early))
    assert policy.last_path == "calibrated"
    late = _mid_game_state(game, rnd=game.rounds)          # rounds_left-after-this = 1 <= endgame_rounds
    policy._accept_prob_table(late, policy._tables(late))
    assert policy.last_path == "calibrated-vote"


# --------------------------------------------------------------------------- direction --
def test_empirical_offer_model_lowers_the_reservation():
    """The intervention's mechanism: a thin measured incoming-offer stream is worth less than the Bayesian
    imagined one, so the calibrated reservation must sit below the Bayesian reservation at the same state."""
    game = _game(0)
    state = _mid_game_state(game, rnd=1)
    thin = _offer_curves(levels=((0.02, 0.05, 0.10), (0.05, 0.10, 0.20)))
    calib = LLMCalibratedRationalPolicy(model=_model(offers=thin), opponent_model=MODEL)
    step_only = LLMCalibratedRationalPolicy(model=LLMOpponentModel.step(), opponent_model=MODEL)
    assert calib.reservation(state) < step_only.reservation(state)


def test_walk_if_hopeless_still_fires():
    game = _game(0)
    hopeless = OfferCurveSet(curves={MODEL: OfferCurve(frac_edges=(), z_quantiles=((-0.5, -0.2),))})
    # p_max=0 clamps the fitted probability to an exact zero: nothing can pass, incoming offers are all
    # below threshold, and it is the final round — the one situation the walk rule exists for. (A merely
    # tiny pass probability must NOT walk; that parity with the parent is covered by the step-model tests.)
    never = AcceptanceCurveSet(z_space="surplus_norm",
                               curves={MODEL: AcceptanceCurve(form="logistic", params={"a": -30.0, "b": 0.0},
                                                              p_min=0.0, p_max=0.0)})
    policy = LLMCalibratedRationalPolicy(model=_model(acceptance=never, offers=hopeless),
                                         opponent_model=MODEL)
    state = _mid_game_state(game, rnd=6, deadline=6)       # last round, nothing can pass, offers are all bad
    assert isinstance(policy(state), Walk)
