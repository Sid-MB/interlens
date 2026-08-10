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

# [rational_agents: fairness-arms] 2026-08-07
"""Tests for the two fairness-seeking negotiators — ``fairness-oracle`` and ``fairness-rational``.

Three layers.

The **property layer** pins the claims that justify calling these agents "fairness" agents at all, on
randomly generated games rather than one hand-picked fixture: at full information the objective's argmax is
*exactly* the discrete Nash Bargaining Solution when some deal clears every threshold, and exactly the Maximum
Nash Welfare point when none does; the objective's ordering on the individually-rational region is exactly the
normalized-Nash-welfare ordering; and a solo table degenerates to the planner's pick. These are equalities
against ``solutions.py``, computed by a completely independent route, so they have teeth.

The **unit layer** pins the decision rules on hand-built states — that the fairness oracle actually proposes
something different from the self-interested oracle where the two disagree (otherwise every other test here is
vacuous), that it still refuses to sign below its own threshold, and that the private variant's posterior
readout matches a brute-force computation over the type grid.

The **regression layer** pins the thing most likely to break silently: the objective parameter threaded
through ``acceptance.py`` / ``bestresponse.py`` defaults to the previous behaviour, so an ordinary
``bayes-rational`` seat must be bit-identical to what it was before the seam existed.
"""
from __future__ import annotations

import numpy as np
import pytest

from interlens.arena.actions import Accept, Propose, Walk
from interlens.arena.negotiation import fairness, solutions
from interlens.arena.negotiation.acceptance import AcceptanceOracle, offer_surplus_pmf
from interlens.arena.negotiation.beliefs import BeliefOracle, BeliefState
from interlens.arena.negotiation.bestresponse import BestResponseOracle
from interlens.arena.negotiation.generate import generate_game
from interlens.arena.negotiation.oracle_context import GameTables
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet, utility_matrix
from interlens.arena.negotiation.space import DealSpace, Issue
from interlens.arena.negotiation.strategies import (BayesianRationalPolicy, FairnessOraclePolicy,
                                                    FairnessRationalPolicy, NegotiationState)
from interlens.arena.table import POLICY_FACTORIES


def _tables_and_arrays(game: GameSpec):
    """``(GameTables, U, tau)`` for a game — the two independent routes to the same numbers, so the property
    tests can compare the policy stack's view against ``solutions.py``'s."""
    tables = GameTables.from_game(game)
    U = utility_matrix(game.space, game.sheets)
    tau = np.array([s.threshold for s in game.sheets], dtype=float)
    return tables, U, tau


def _generated_games(n=12, **kw):
    """A spread of solver-verified games, so a property is checked against many geometries rather than one."""
    out = []
    for seed in range(n):
        game, _info = generate_game(seed=seed, **kw)
        out.append(game)
    return out


# --------------------------------------------------------------------------------------------------------- #
# Property layer: the objective IS the Nash bargaining / MNW point.
# --------------------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("n_parties", [2, 3, 5])
def test_objective_argmax_is_the_nash_bargaining_deal(n_parties):
    """THE headline property: whenever some deal clears every party's threshold, maximizing the table
    objective picks exactly the discrete NBS deal — the deal ``solutions.py`` names by an independent route.

    Scoped to a non-empty strict-IR set on purpose, because that is where the claim is actually exact. See
    :func:`test_objective_agrees_with_mnw_on_coalition_size_when_no_deal_satisfies_everyone` for what survives
    when it is empty, and why the two definitions part company there."""
    checked = 0
    for game in _generated_games(12, n_parties=n_parties, n_issues=3):
        tables, U, tau = _tables_and_arrays(game)
        if not solutions.ir_mask(U, tau, strict=True).any():
            continue
        obj = fairness.mnw_objective(tables)
        best = fairness.max_objective_index(obj)
        nbs, ties, _note = solutions.nash_bargaining_index(U, tau)
        # Compare against the whole tie set: two deals with identical surplus vectors are the same point, and
        # the two routes need not break that tie identically.
        assert best in ties, f"objective picked {best}, NBS tie set is {ties}"
        assert obj[best] == pytest.approx(obj[nbs])
        checked += 1
    assert checked >= 4, "too few usable games — the property would be vacuous"


def test_objective_agrees_with_mnw_on_coalition_size_when_no_deal_satisfies_everyone():
    """When the strict-IR set is empty, the objective must still follow Maximum Nash Welfare's *first* stage —
    satisfy the largest coalition it can — rather than going flat.

    It does NOT reproduce MNW's second stage exactly, and that is a deliberate, documented divergence rather
    than a near-miss. ``solutions.max_nash_welfare_index`` ranks same-size coalitions by the product of RAW
    surpluses; this objective ranks them by the geometric mean of NORMALIZED ones. The two coincide when the
    coalition is everybody (the per-party normalizers are then a common constant that cancels) but not when it
    varies, because the normalizers no longer cancel across candidate coalitions. We keep the normalized
    version because scale invariance across private point scales is the property this whole program's
    judgment metric rests on; the price is that off the IR set the two definitions can name different deals.
    Checked here on a spread of real games, not just the symmetric fixture below."""
    space = DealSpace((Issue("I", ("X", "Y", "Z")),))
    # No option clears all three thresholds: X suits p0, Y suits p1, Z suits nobody.
    sheets = (ScoreSheet("p0", ((10.0, 1.0, 0.0),), threshold=5.0),
              ScoreSheet("p1", ((1.0, 10.0, 0.0),), threshold=5.0),
              ScoreSheet("p2", ((1.0, 1.0, 0.0),), threshold=5.0))
    game = GameSpec(space, sheets, rounds=2, info="full", proposer=0, chat=False)
    tables, U, tau = _tables_and_arrays(game)
    assert not solutions.ir_mask(U, tau, strict=True).any(), "fixture must have an EMPTY strict-IR set"

    obj = fairness.mnw_objective(tables)
    mnw, ties, _note = solutions.max_nash_welfare_index(U, tau)
    assert fairness.max_objective_index(obj) in ties
    # ...and the objective is genuinely informative here rather than a constant.
    assert obj.max() > obj.min()

    # The general claim, on randomized over-constrained games: same coalition SIZE as MNW, every time. The
    # generator's solver-verified banks essentially always admit a fully-IR deal, so this regime has to be
    # constructed — thresholds set above what any single deal can satisfy for everyone.
    rng = np.random.default_rng(0)
    space4 = DealSpace(tuple(Issue(f"I{j}", ("a", "b", "c")) for j in range(2)))
    checked = 0
    for _ in range(40):
        sheets = tuple(ScoreSheet(f"p{i}", tuple(tuple(rng.integers(0, 10, 3).astype(float))
                                                 for _ in range(2)), threshold=9.0) for i in range(4))
        game = GameSpec(space4, sheets, rounds=2, info="full", proposer=0, chat=False)
        tables, U, tau = _tables_and_arrays(game)
        if solutions.ir_mask(U, tau, strict=True).any():
            continue
        mnw, _ties, _note = solutions.max_nash_welfare_index(U, tau)
        picked = fairness.max_objective_index(fairness.mnw_objective(tables))
        assert (U[picked] - tau > 0).sum() == (U[mnw] - tau > 0).sum()
        checked += 1
    assert checked >= 20, f"only {checked} empty-strict-IR games — the sweep is not exercising the branch"


def test_objective_ordering_on_the_ir_region_is_exactly_normalized_nash_welfare():
    """On deals that satisfy everyone the objective is ``1 + NNW/n``, so it induces precisely the NNW ranking
    the campaign judges outcomes by — the policy optimizes the metric, not a proxy for it."""
    game = next(g for g in _generated_games(12, n_parties=4, n_issues=3)
                if np.all(utility_matrix(g.space, g.sheets)
                          - np.array([s.threshold for s in g.sheets]) > 0, axis=1).sum() >= 5)
    tables, U, tau = _tables_and_arrays(game)
    obj = fairness.mnw_objective(tables)
    z = np.clip(fairness.normalized_surplus_matrix(tables), 0.0, 1.0)
    n = U.shape[1]

    ir = np.nonzero(np.all(U - tau > 0, axis=1))[0]
    nnw = np.exp(np.log(z[ir]).mean(axis=1))
    assert obj[ir] == pytest.approx(1.0 + nnw / n)
    # ranking identity, stated directly
    assert list(np.argsort(-obj[ir])) == list(np.argsort(-nnw))


def test_every_deal_outside_the_ir_region_scores_below_every_deal_inside_it():
    """The coalition term must dominate the welfare term — that is what makes the flattening lexicographic
    (MNW's "largest satisfiable coalition first") rather than a tunable trade-off between the two."""
    for game in _generated_games(8, n_parties=4, n_issues=3):
        tables, U, tau = _tables_and_arrays(game)
        obj = fairness.mnw_objective(tables)
        full = np.all(U - tau > 0, axis=1)
        if not full.any() or full.all():
            continue
        assert obj[full].min() > obj[~full].max()


def test_no_deal_scores_zero_on_the_objective():
    """The recursion in ``acceptance.py`` has ``v_0 = 0`` meaning "never agreeing". A substituted objective
    must keep that convention or the optimal-stopping comparison is between incommensurable units."""
    space = DealSpace((Issue("I", ("X",)),))
    sheets = (ScoreSheet("p0", ((1.0,),), threshold=5.0), ScoreSheet("p1", ((1.0,),), threshold=5.0))
    game = GameSpec(space, sheets, rounds=2, info="full", proposer=0, chat=False)
    tables, _U, _tau = _tables_and_arrays(game)
    # The single deal satisfies nobody, so it scores the same as no deal at all.
    assert fairness.mnw_objective(tables) == pytest.approx(np.array([0.0]))


def test_solo_table_degenerates_to_the_planner():
    """With one seat there is nobody to bargain with, and the fairness objective must reduce to "pick the best
    feasible outcome" — the planner's choice, and identical to what the self-interested agent would do."""
    space = DealSpace((Issue("I", ("X", "Y", "Z")),))
    sheet = ScoreSheet("p0", ((1.0, 9.0, 4.0),), threshold=0.0)
    game = GameSpec(space, (sheet,), rounds=2, info="full", proposer=0, chat=False)
    tables, U, tau = _tables_and_arrays(game)

    obj = fairness.mnw_objective(tables)
    planner = int(np.argmax(U[:, 0] - tau[0]))
    assert fairness.max_objective_index(obj) == planner == 1
    # and the objective's ranking is the planner's ranking, not merely its argmax
    assert list(np.argsort(-obj)) == list(np.argsort(-(U[:, 0] - tau[0])))


def test_fairness_oracle_policy_proposes_the_nash_bargaining_deal_at_full_information():
    """The property carried all the way through the POLICY, not just the objective function: the seated
    ``fairness-oracle`` tables the NBS deal on its opening move."""
    for game in _generated_games(6, n_parties=4, n_issues=3):
        tables, U, tau = _tables_and_arrays(game)
        if not solutions.ir_mask(U, tau, strict=True).any():
            continue
        state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=1, deadline=game.rounds,
                                 tables=tables, opponents=(1, 2, 3))
        action = FairnessOraclePolicy()(state)
        assert isinstance(action, Propose)
        _nbs, ties, _note = solutions.nash_bargaining_index(U, tau)
        assert tables.index[action.deal] in ties


# --------------------------------------------------------------------------------------------------------- #
# Unit layer: the two policies actually behave differently from the self-interested one.
# --------------------------------------------------------------------------------------------------------- #
def _conflict_game():
    """A game where seat 0's own optimum and the table's fair point are DIFFERENT deals, so a test comparing
    the two objectives cannot pass by coincidence."""
    space = DealSpace((Issue("I", ("X", "Y", "Z")),))
    sheets = (ScoreSheet("p0", ((10.0, 6.0, 0.0),), threshold=1.0),      # loves X
              ScoreSheet("p1", ((2.0, 6.0, 3.0),), threshold=1.0),       # Y is much better than X
              ScoreSheet("p2", ((2.0, 6.0, 3.0),), threshold=1.0))       # likewise
    return GameSpec(space, sheets, rounds=3, info="full", proposer=0, chat=False)


def test_fairness_oracle_proposes_the_fair_deal_where_the_selfish_oracle_proposes_its_own_best():
    """The teeth: on a game built so the two objectives disagree, swapping the objective must swap the move."""
    game = _conflict_game()
    tables, U, tau = _tables_and_arrays(game)
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=1, deadline=game.rounds,
                             tables=tables, opponents=(1, 2))

    selfish = BayesianRationalPolicy()(state)
    fair = FairnessOraclePolicy()(state)
    assert isinstance(selfish, Propose) and isinstance(fair, Propose)
    assert selfish.deal != fair.deal, "objectives must disagree on this fixture or the test proves nothing"
    assert fair.deal == (1,)                                   # Y: the Nash point
    nbs, _ties, _note = solutions.nash_bargaining_index(U, tau)
    assert tables.index[fair.deal] == nbs
    # the fair deal is worse for seat 0 and better for the table — the whole point of the swap
    assert U[tables.index[fair.deal], 0] < U[tables.index[selfish.deal], 0]
    assert (U[tables.index[fair.deal]] - tau).min() > (U[tables.index[selfish.deal]] - tau).min()


def test_fairness_oracle_refuses_to_sign_below_its_own_threshold():
    """Objective swap or not, no variant of this policy agrees to a deal that is worse for it than no deal —
    the scenario records that as an individual-rationality violation."""
    space = DealSpace((Issue("I", ("X", "Y")),))
    sheets = (ScoreSheet("p0", ((0.0, 9.0),), threshold=5.0),            # X is BELOW seat 0's threshold
              ScoreSheet("p1", ((9.0, 0.0),), threshold=1.0),
              ScoreSheet("p2", ((9.0, 0.0),), threshold=1.0))
    game = GameSpec(space, sheets, rounds=3, info="full", proposer=0, chat=False)
    tables, _U, _tau = _tables_and_arrays(game)
    state = NegotiationState(seat=0, sheet=sheets[0], space=game.space, round=2, deadline=3, tables=tables,
                             offers={"P1": (0,)}, standing="P1", received=[(0,)], opponents=(1, 2))
    assert not isinstance(FairnessOraclePolicy()(state), Accept)
    # ...and on the terminal forced vote too
    vote_state = NegotiationState(seat=0, sheet=sheets[0], space=game.space, round=4, deadline=3,
                                  tables=tables, offers={"P1": (0,)}, standing="P1", must_vote=True,
                                  opponents=(1, 2))
    assert not isinstance(FairnessOraclePolicy()(vote_state), Accept)


def test_fairness_rational_matches_the_oracle_when_it_is_given_full_information():
    """The two agents differ ONLY in what they know. Hand the private one the sheets and the difference must
    vanish — which is what licenses reading their gap as the price of private information."""
    game = _conflict_game()
    tables, _U, _tau = _tables_and_arrays(game)
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=1, deadline=game.rounds,
                             tables=tables, opponents=(1, 2))
    assert FairnessRationalPolicy()(state).deal == FairnessOraclePolicy()(state).deal


def test_fairness_rational_acts_legally_under_private_information():
    """The private agent has no ``state.tables``: its objective comes off the posterior. It must still return
    a well-formed, individually-rational proposal rather than crashing on the padded table."""
    game = _conflict_game()
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=1, deadline=game.rounds,
                             tables=None, opponents=(1, 2),
                             received=[(1,), (2,)], received_by_opponent={1: [(1,)], 2: [(2,)]})
    action = FairnessRationalPolicy()(state)
    assert isinstance(action, Propose)
    assert game.sheets[0].surplus(action.deal) >= 0


def test_private_objective_is_a_proper_expected_welfare_vector():
    """The estimated objective must be a real objective: finite, on the same ``[0, 1 + 1/n]`` scale as the
    exact one, and not degenerate (a constant column would make every proposal a coin flip)."""
    game = _conflict_game()
    policy = FairnessRationalPolicy()
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=2, deadline=3,
                             tables=None, opponents=(1, 2),
                             received=[(1,)], received_by_opponent={1: [(1,)], 2: [(1,)]})
    obj = policy._objective(state, policy._tables(state))
    assert obj.shape == (game.space.size,)
    assert np.all(np.isfinite(obj))
    assert obj.min() >= 0.0 and obj.max() <= 1.0 + 1.0 / 3 + 1e-9
    assert obj.max() > obj.min()


def test_expected_normalized_surplus_matches_a_brute_force_posterior_mixture():
    """The belief readout the private agent's objective is built on, checked against the definition computed
    type by type — and the cached full-space path checked against the on-the-fly one."""
    st = BeliefState((3, 2))
    st.observe((0, 0)).observe((0, 1))
    deals_arr = np.array([[i, j] for i in range(3) for j in range(2)], dtype=int)

    post = st.posterior()
    rows = []
    for t in st.types:
        x = np.array([max(t.utility(tuple(d)) - t.threshold, 0.0) for d in deals_arr])
        b = x.max()
        rows.append(x / (b if b > 0 else 1.0))
    expected = post @ np.array(rows)

    got = st.expected_normalized_surplus_matrix(deals_arr)
    assert got == pytest.approx(expected, abs=1e-9)
    assert np.all((got >= 0.0) & (got <= 1.0))
    # A partial batch takes the on-the-fly path; it must return the same numbers as the corresponding slice of
    # the full one, which is only true if both normalize by the type's ideal over the WHOLE space.
    assert st.expected_normalized_surplus_matrix(deals_arr[:4]) == pytest.approx(expected[:4], abs=1e-9)


def test_both_policies_are_registered_and_self_naming():
    for name, cls in (("fairness-oracle", FairnessOraclePolicy), ("fairness-rational", FairnessRationalPolicy)):
        assert name in POLICY_FACTORIES
        assert isinstance(POLICY_FACTORIES[name](), cls)
        assert POLICY_FACTORIES[name]().name == name


# --------------------------------------------------------------------------------------------------------- #
# Regression layer: the objective seam is inert unless used.
# --------------------------------------------------------------------------------------------------------- #
def test_objective_defaults_reproduce_the_self_interested_numbers_exactly():
    """Every function that grew an ``objective`` parameter must be bit-identical when it is omitted, and
    identical again when passed the seat's own surplus column explicitly."""
    game, _info = generate_game(seed=2, n_parties=3, n_issues=3)
    tables = GameTables.from_game(game)
    own = tables.surplus[:, 0]
    ap = (tables.surplus >= 0.0).astype(float)
    ap[:, 0] = 1.0

    v_a, p_a = offer_surplus_pmf(tables, 0)
    v_b, p_b = offer_surplus_pmf(tables, 0, objective=own)
    assert np.array_equal(v_a, v_b) and np.array_equal(p_a, p_b)

    acc = AcceptanceOracle(0, discount=0.95)
    assert acc.reservation(tables, 3) == acc.reservation(tables, 3, objective=own)

    br = BestResponseOracle(0, discount=0.95, accept_prob=ap)
    cont = np.zeros(tables.n_agents)
    assert np.array_equal(br.propose_values(tables, cont), br.propose_values(tables, cont, objective=own))


def test_bayes_rational_is_unchanged_by_the_seam():
    """End to end: the ordinary rational agent's move on a real state must not have moved."""
    game = _conflict_game()
    tables, _U, _tau = _tables_and_arrays(game)
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=1, deadline=game.rounds,
                             tables=tables, opponents=(1, 2))
    action = BayesianRationalPolicy()(state)
    # seat 0's own optimum, which is what a self-interested best-responder tables when everyone can accept
    assert isinstance(action, Propose) and action.deal == (0,)
    assert BayesianRationalPolicy()._objective(state, tables) is None


def test_fit_belief_gives_every_consumer_the_same_posterior():
    """The private fairness agent reads beliefs twice per turn (acceptance probabilities and the objective's
    opponent columns). Both must come off the same fitted posterior, or the agent believes two things."""
    from interlens.arena.negotiation.strategies import fit_belief
    game = _conflict_game()
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=2, deadline=3,
                             tables=None, opponents=(1, 2),
                             received=[(1,)], received_by_opponent={1: [(1,)], 2: [(2,)]})
    a, b = fit_belief(state), fit_belief(state)
    assert isinstance(a, BeliefOracle) and set(a.states) == {1, 2}
    for opp in (1, 2):
        assert a.states[opp].posterior() == pytest.approx(b.states[opp].posterior())


# --------------------------------------------------------------------------------------------------------- #
# The refusal on the PROPOSE branch — the one the objective cannot supply for itself.
# --------------------------------------------------------------------------------------------------------- #
def _self_sacrifice_game():
    """A game whose table-welfare optimum tramples seat 0.

    One issue, two options. ``Y`` pays seat 0 well and the other four nothing; ``X`` pays the other four well
    and puts seat 0 nine points under its threshold. Maximizing the table's welfare over a clipped own-surplus
    column therefore points straight at ``X``, which is precisely the configuration where an objective that is
    indifferent to its own losses will table a deal that harms the seat holding it.
    """
    space = DealSpace((Issue("I", ("X", "Y")),))
    sheets = (ScoreSheet("p0", ((0.0, 20.0),), threshold=9.0),
              *(ScoreSheet(f"p{i}", ((20.0, 0.0),), threshold=1.0) for i in range(1, 5)))
    return GameSpec(space, sheets, rounds=3, info="full", proposer=0, chat=False)


@pytest.mark.parametrize("policy_cls", [FairnessOraclePolicy, FairnessRationalPolicy])
def test_fairness_policies_never_propose_a_deal_below_their_own_threshold(policy_cls):
    """The regression this pins cost a campaign re-run. The parent class guards accepting and voting, but not
    proposing — and it does not need to for a self-interested agent, whose own-surplus argmax rejects a
    self-harming deal automatically. A table objective scores own surplus as ``clip(u - tau, 0)``, so it is
    exactly indifferent between sitting at the threshold and sitting far below it, and will table a package
    that pays everyone else out of this seat's own hide. Measured before the fix: the omniscient variant closed
    4 of 120 campaign games below its own threshold and the private one 15 of 55, always as the proposer, while
    the matched self-interested control violated individual rationality zero times in 120.
    """
    game = _self_sacrifice_game()
    tables, _U, _tau = _tables_and_arrays(game)
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=1, deadline=game.rounds,
                             tables=tables, opponents=(1, 2, 3, 4))
    action = policy_cls()(state)
    assert isinstance(action, Propose)
    assert action.deal == (1,), "must table Y (its own IR option), not the table-welfare-maximal X"
    assert game.sheets[0].surplus(action.deal) >= 0


def test_the_objective_really_does_prefer_the_self_sacrificing_deal():
    """Gives the test above its teeth: without the filter the objective's argmax IS the trampling deal, so the
    assertion is checking the guard rather than a game where the two happen to coincide."""
    game = _self_sacrifice_game()
    tables, _U, _tau = _tables_and_arrays(game)
    objective = fairness.mnw_objective(tables)
    assert int(np.argmax(objective)) == 0, "expected X (index 0) to be the table-welfare optimum"
    assert game.sheets[0].surplus((0,)) < 0


def test_the_self_interested_agent_is_untouched_by_the_proposal_filter():
    """The filter lives on the fairness base class only. The ordinary Bayesian agent's proposals are replayed
    and re-annotated across completed campaigns, so its choice must not move."""
    game = _self_sacrifice_game()
    tables, _U, _tau = _tables_and_arrays(game)
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=1, deadline=game.rounds,
                             tables=tables, opponents=(1, 2, 3, 4))
    action = BayesianRationalPolicy()(state)
    assert isinstance(action, Propose) and action.deal == (1,)
    assert BayesianRationalPolicy()._pick_proposal(np.array([5.0, 1.0]), None, tables, 0) == 0


def test_the_filter_falls_back_when_no_deal_clears_the_seats_threshold():
    """In a game where every option is below this seat's threshold there is nothing to protect, and the agent
    should still name the best table outcome rather than be left with an empty candidate set."""
    space = DealSpace((Issue("I", ("X", "Y")),))
    sheets = (ScoreSheet("p0", ((0.0, 1.0),), threshold=50.0),
              ScoreSheet("p1", ((9.0, 0.0),), threshold=1.0),
              ScoreSheet("p2", ((9.0, 0.0),), threshold=1.0))
    game = GameSpec(space, sheets, rounds=3, info="full", proposer=0, chat=False)
    tables, _U, _tau = _tables_and_arrays(game)
    state = NegotiationState(seat=0, sheet=sheets[0], space=game.space, round=1, deadline=3, tables=tables,
                             opponents=(1, 2))
    assert isinstance(FairnessOraclePolicy()(state), (Propose, Walk))
