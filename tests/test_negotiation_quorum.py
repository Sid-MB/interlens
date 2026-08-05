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

"""Focused regression tests for fixed-seat quorum negotiation semantics."""
from __future__ import annotations

import json

import numpy as np

from interlens.arena.negotiation.bestresponse import (BestResponseOracle, conditional_vote_values,
                                                       passage_probability,
                                                       value_to_go_beliefs, value_to_go_full_info)
from interlens.arena.actions import Accept, Reject, Walk
from interlens.arena.negotiation.oracle_context import GameTables
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet
from interlens.arena.negotiation.space import DealSpace, Issue
from interlens.arena.negotiation.strategies import BayesianRationalPolicy, NegotiationState
from interlens.arena.schema import Instance, PERSONAS, new_id
from interlens.arena.scenarios.scorable import ScorableNegotiation


def _game(*, min_accept: int | None, veto=None, rounds: int = 1) -> GameSpec:
    space = DealSpace((Issue("Package", ("Coalition", "Universal")),))
    # Coalition: seats 0--3 clear, seat 4 does not. Universal: everyone clears, but proposer 0 gets less.
    sheets = (
        ScoreSheet("S0", ((10.0, 5.0),), 0.0),
        ScoreSheet("S1", ((1.0, 1.0),), 0.0),
        ScoreSheet("S2", ((1.0, 1.0),), 0.0),
        ScoreSheet("S3", ((1.0, 1.0),), 0.0),
        ScoreSheet("S4", ((-1.0, 1.0),), 0.0),
    )
    return GameSpec(space, sheets, rounds=rounds, info="full", proposer=0,
                    min_accept=min_accept, veto=veto)


def _instance(game: GameSpec) -> Instance:
    return Instance(new_id("quorum-test"), ScorableNegotiation.name, 0, 0,
                    payload=game.to_json(), ceiling=1.0, floor=0.0, solution={})


def _apply_next(scenario: ScorableNegotiation, state: dict, action: dict) -> None:
    if action.get("offer_id") == "LIVE":
        action = {**action, "offer_id": state["registry"].standing_ids()[0]}
    req = scenario.next_requests(state)[0]
    text = "```json\n" + json.dumps(action) + "\n```"
    assert scenario.apply(state, req, text) is None


def test_fixed_quorum_does_not_shrink_after_walks():
    scenario = ScorableNegotiation()
    state = scenario.make_state(_instance(_game(min_accept=4, rounds=2)), "moves_chat", seed=0)
    _apply_next(scenario, state, {"action": "propose", "deal": {"Package": "Coalition"}})
    _apply_next(scenario, state, {"action": "accept", "offer_id": "LIVE"})
    _apply_next(scenario, state, {"action": "accept", "offer_id": "LIVE"})
    _apply_next(scenario, state, {"action": "walk"})
    assert not state["done"] and len(scenario._active_idxs(state)) == 4

    # There are three supporting seats. The historical min(4, active=3) bug closed O1 after this walk.
    _apply_next(scenario, state, {"action": "walk"})
    assert state["done"]
    assert state["final_deal"] is None and state["finalized_by"] == "no_deal"


def test_numeric_quorum_closes_early_and_veto_walk_ends_no_deal():
    scenario = ScorableNegotiation()
    state = scenario.make_state(_instance(_game(min_accept=3)), "moves_chat", seed=0,
                                cfg={"single_shot": True})
    _apply_next(scenario, state, {"action": "propose", "deal": {"Package": "Coalition"}})
    _apply_next(scenario, state, {"action": "accept", "offer_id": "LIVE"})
    _apply_next(scenario, state, {"action": "accept", "offer_id": "LIVE"})
    assert state["done"] and state["closing_offer"] == state["final_offer"]
    assert len(state["events"]) == 3  # proposer plus the two votes needed for the fixed 3/5 quorum

    vetoed = scenario.make_state(_instance(_game(min_accept=3, veto=2)), "moves_chat", seed=0)
    _apply_next(scenario, vetoed, {"action": "propose", "deal": {"Package": "Coalition"}})
    _apply_next(scenario, vetoed, {"action": "accept", "offer_id": "LIVE"})
    _apply_next(scenario, vetoed, {"action": "walk"})
    assert vetoed["done"] and vetoed["final_deal"] is None


def test_quorum_passage_probability_and_veto_are_exact():
    ap = np.full((1, 5), 0.5)
    ap[:, 0] = 1.0
    assert passage_probability(ap, 0, min_accept=3)[0] == 0.6875
    assert passage_probability(ap, 0, min_accept=4)[0] == 0.3125
    assert passage_probability(ap, 0, min_accept=None)[0] == 0.0625
    assert passage_probability(ap, 0, min_accept=3, veto_seats=(4,))[0] == 0.4375


def test_best_response_and_bayesian_dp_use_game_quorum():
    quorum_game = _game(min_accept=4)
    unanimous_game = _game(min_accept=None)
    tq, tu = GameTables.from_game(quorum_game), GameTables.from_game(unanimous_game)
    cont = np.zeros(5)

    q_values = BestResponseOracle(0, min_accept=4).propose_values(tq, cont)
    u_values = BestResponseOracle(0).propose_values(tu, cont)
    assert int(np.argmax(q_values)) == 0       # exploit the four-seat winning coalition
    assert int(np.argmax(u_values)) == 1       # must compensate every responder
    veto_values = BestResponseOracle(0, min_accept=4, veto_seats=(4,)).propose_values(tq, cont)
    assert int(np.argmax(veto_values)) == 1

    ap = (tq.surplus >= 0.0).astype(float)
    ap[:, 0] = 1.0
    vi_q = value_to_go_beliefs(tq, 0, range(5), 1, 1.0, ap, {}, min_accept=4)
    vi_u = value_to_go_beliefs(tq, 0, range(5), 1, 1.0, ap, {}, min_accept=None)
    assert vi_q[1] == 10.0 and vi_u[1] == 5.0

    state = NegotiationState(seat=0, sheet=quorum_game.sheets[0], space=quorum_game.space,
                             deadline=1, tables=tq, opponents=(1, 2, 3, 4), min_accept=4)
    assert BayesianRationalPolicy().act(state).deal == (0,)


def test_current_vote_values_pivotal_and_non_pivotal_quorum_actions():
    game = _game(min_accept=3)
    # Four Avery-style public supporters mean Emery's no vote is non-pivotal. Both votes realize the deal,
    # including its -1 surplus; WALK is explicitly the outside option 0.
    history = {
        "round": 1, "seat_names": list(PERSONAS[:5]), "walked": [],
        "offers": [{"offer_id": "P1", "deal": [0], "proposer": PERSONAS[0],
                    "accepts": list(PERSONAS[:4]), "rejects": [], "live": True}],
    }
    verdict = BestResponseOracle(4).evaluate(
        game, history, 4, [Accept("P1"), Reject("P1"), Walk()])
    assert verdict.value_of(Accept("P1")) == -1.0
    assert verdict.value_of(Reject("P1")) == -1.0
    assert verdict.value_of(Walk()) == 0.0
    assert verdict.best == Walk()

    # Conversely, one deciding yes cannot force a 4/5 deal when the proposer is the only other supporter.
    ap = np.zeros((1, 5))
    ap[0, 0] = 1.0
    yes, no, q_yes, q_no = conditional_vote_values(
        ap, proposer=0, agent=4, deal_index=0, deal_surplus=8.0, continuation=2.0,
        min_accept=4, forced_yes=(0,))
    assert (q_yes, q_no) == (0.0, 0.0)
    assert (yes, no) == (2.0, 2.0)


def test_bayesian_terminal_vote_uses_offer_provenance_and_cast_votes():
    game = _game(min_accept=4)
    tables = GameTables.from_game(game)
    # On Coalition, proposer + seats 1/2 already support. Seat 3 is pivotal for 4/5 and rationally accepts.
    pivotal = NegotiationState(
        seat=3, sheet=game.sheets[3], space=game.space, deadline=1, round=2, must_vote=True,
        tables=tables, opponents=(0, 1, 2, 4), min_accept=4, offers={"P1": (0,)}, standing="P1",
        offer_proposers={"P1": 0}, offer_accepts={"P1": (0, 1, 2)})
    assert BayesianRationalPolicy()(pivotal) == Accept("P1")

    # With only the proposer supporting, this seat's yes cannot reach 4/5; accepting is not recommended.
    failing = NegotiationState(
        seat=3, sheet=game.sheets[3], space=game.space, deadline=1, round=2, must_vote=True,
        tables=tables, opponents=(0, 1, 2, 4), min_accept=4, offers={"P1": (0,)}, standing="P1",
        offer_proposers={"P1": 0}, offer_accepts={"P1": (0,)}, offer_rejects={"P1": (1, 2)})
    assert BayesianRationalPolicy()(failing) == Reject("P1")


def test_unanimity_default_is_backward_compatible():
    tables = GameTables.from_game(_game(min_accept=None, rounds=3))
    seq = range(5)
    implicit = value_to_go_full_info(tables, seq, 3, 0.9)
    explicit = value_to_go_full_info(tables, seq, 3, 0.9, min_accept=5)
    np.testing.assert_allclose(implicit, explicit)
