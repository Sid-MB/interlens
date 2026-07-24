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

# [rational_agents scaffold: oracles-strategies] 2026-07-23
"""Tests for the negotiation oracle stack (beliefs / acceptance / bestresponse / equilibrium / strategies)
and the PolicyParticipant. Each closed-form / sanity anchor from DESIGN.md §8 is pinned here."""
from __future__ import annotations

import itertools

import numpy as np
import pytest

from interlens import Conversation, RoundRobinPolicy
from interlens.arena.actions import Accept, Propose, Reject, Walk, parse_action
from interlens.arena.negotiation.space import DealSpace, Issue
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet
from interlens.arena.negotiation._oracle_common import GameTables, NegotiationState

from interlens.arena.negotiation.acceptance import AcceptanceOracle, ThresholdOracle, reservation_values
from interlens.arena.negotiation.beliefs import BeliefState, FrequencyModel, OpponentType
from interlens.arena.negotiation.bestresponse import BestResponseOracle, value_to_go_full_info
from interlens.arena.negotiation.equilibrium import (EquilibriumOracle, divide_the_dollar, okada_closed_form,
                                                     solve_equilibrium)
from interlens.arena.negotiation.strategies import (ACTime, TimeDependentPolicy, ToughPolicy,
                                                    BayesianRationalPolicy)
from interlens.participant.participants.policy_participant import PolicyParticipant


# --------------------------------------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------------------------------------- #
class Turn0:
    """A minimal turn record (agent name + typed action) for oracle tests, matching the arena Turn shape."""

    def __init__(self, agent, action):
        self.agent = agent
        self.action = action


def _all_deals(counts):
    return [tuple(d) for d in itertools.product(*[range(c) for c in counts])]


def _tiny_game():
    """A 2-party, 1-issue-2-option full-info game with a leverage twist: the deal that pays party 0 more is
    the one party 1 will reject in favor of waiting, so the expectimax best response is the *other* deal."""
    space = DealSpace((Issue("I", ("X", "Y")),))
    s0 = ScoreSheet("p0", ((10.0, 1.0),), threshold=0.0)   # X=10, Y=1
    s1 = ScoreSheet("p1", ((1.0, 10.0),), threshold=0.0)   # X=1,  Y=10
    return GameSpec(space, (s0, s1), rounds=2, info="full", proposer=0, chat=False)


# --------------------------------------------------------------------------------------------------------- #
# 1. Belief oracle: convergence on honest concession, robustness under deception.
# --------------------------------------------------------------------------------------------------------- #
def _three_types():
    oc = (3, 3)
    true = OpponentType((0.8, 0.2), ("downhill", "uphill"), 0.3, oc)
    alt1 = OpponentType((0.2, 0.8), ("uphill", "downhill"), 0.5, oc)
    alt2 = OpponentType((0.5, 0.5), ("triangular", "triangular"), 0.4, oc)
    return true, alt1, alt2


def _concession_trace(t, ascending=False):
    """Deals ordered by ``t``'s own utility (descending = honest concession; ascending = deceptive)."""
    deals = _all_deals(t.option_counts)
    deals.sort(key=lambda d: t.utility(d), reverse=not ascending)
    return deals


def test_belief_converges_on_honest_concession():
    true, alt1, alt2 = _three_types()
    st = BeliefState(true.option_counts, types=[true, alt1, alt2], mode="joint", lam=1.0)
    for d in _concession_trace(true)[:6]:
        st.observe(d)
    post = dict(zip(st.types, st.posterior()))
    assert st.map_type() is true
    assert post[true] > 0.6                     # concentrates on the true type
    assert post[true] > post[alt1] and post[true] > post[alt2]


def test_belief_damping_resists_deception():
    true, alt1, alt2 = _three_types()
    trace = _concession_trace(true, ascending=True)[:6]   # anti-concession = deceptive
    damped = BeliefState(true.option_counts, types=[true, alt1, alt2], mode="joint", lam=0.2)
    undamped = BeliefState(true.option_counts, types=[true, alt1, alt2], mode="joint", lam=1.0)
    for d in trace:
        damped.observe(d)
        undamped.observe(d)
    pd = dict(zip(damped.types, damped.posterior()))[true]
    pu = dict(zip(undamped.types, undamped.posterior()))[true]
    assert pd > pu                               # damping keeps more mass on the truth under deception
    assert max(damped.posterior()) < 0.99        # posterior not catastrophically collapsed


def test_frequency_model_tracks_offers():
    true, _, _ = _three_types()
    fm = FrequencyModel(true.option_counts)
    for d in _concession_trace(true)[:6]:
        fm.update(d)
    # the frequency model should weight the issue the true type cares about (issue 0) most
    assert int(np.argmax(fm.weights())) == int(np.argmax(true.weights))


# --------------------------------------------------------------------------------------------------------- #
# 2. Acceptance oracle: Baarslag-Hindriks uniform closed form v_j = 1/2 + v_{j-1}^2 / 2 (Prop. 3.1).
# --------------------------------------------------------------------------------------------------------- #
def test_acceptance_uniform_closed_form():
    N = 4000
    values = np.linspace(0.0, 1.0, N)
    probs = np.full(N, 1.0 / N)
    v = reservation_values(values, probs, T=5, cost=0.0, discount=1.0, flow=0.0)
    # closed form
    cf = [0.0]
    for _ in range(5):
        cf.append(0.5 + cf[-1] ** 2 / 2.0)
    assert v[1] == pytest.approx(0.5, abs=2e-3)
    assert v[2] == pytest.approx(0.625, abs=2e-3)
    for j in range(1, 6):
        assert v[j] == pytest.approx(cf[j], abs=3e-3)


def test_acceptance_oracle_flags_premature_accept():
    # A standing offer strictly below the reservation should be flagged and valued below rejecting.
    game = _tiny_game()
    # party 0 faces a standing offer worth surplus 1 (deal Y); reservation from the closable set is higher.
    hist = [Turn0("p1", Propose((1,)))]          # p1 proposes Y (surplus 1 to p0)
    orc = AcceptanceOracle(0, discount=1.0)
    legal = [Accept("O1"), Walk()]
    verdict = orc.evaluate(game, hist, "p0", legal)
    assert verdict.value_of(Accept("O1")) == pytest.approx(1.0)   # surplus of Y for p0


def test_threshold_oracle_flags_wrong_deal():
    # A game where deal Z is below party 0's threshold: proposing/accepting it is an IR violation.
    space = DealSpace((Issue("I", ("X", "Y", "Z")),))
    s0 = ScoreSheet("p0", ((10.0, 6.0, 1.0),), threshold=5.0)   # Z=1 < tau 5 -> wrong deal
    s1 = ScoreSheet("p1", ((1.0, 6.0, 10.0),), threshold=0.0)
    game = GameSpec(space, (s0, s1), rounds=2, info="full", proposer=0, chat=False)
    hist = [Turn0("p1", Propose((2,)))]                          # p1 proposes Z -> registered O1
    orc = ThresholdOracle()
    verdict = orc.evaluate(game, hist, "p0", [Accept("O1"), Propose((2,)), Propose((0,)), Walk()])
    assert "below_threshold_accept" in verdict.flags
    assert "below_threshold_propose" in verdict.flags
    assert verdict.best == Propose((0,))                        # the IR move (X, surplus 5) dominates
    assert verdict.value_of(Accept("O1")) < 0


# --------------------------------------------------------------------------------------------------------- #
# 3. Best-response oracle: exact expectimax on a 2-party toy (leverage beats myopia).
# --------------------------------------------------------------------------------------------------------- #
def test_value_to_go_full_info_backward_induction():
    game = _tiny_game()
    tables = GameTables.from_game(game)
    V = value_to_go_full_info(tables, [0, 1], T=2, discount=0.9)
    # hand-computed: at t=2 proposer p1 takes Y -> [1,10]; at t=1 proposer p0 must also offer Y (p1 rejects X
    # to wait for Y next round) -> [1,10].
    assert np.allclose(V[1], [1.0, 10.0])
    assert np.allclose(V[2], [1.0, 10.0])


def test_bestresponse_picks_dominant_proposal():
    game = _tiny_game()
    orc = BestResponseOracle(0, discount=0.9)
    legal = [Propose((0,)), Propose((1,))]       # X (myopically better for p0) vs Y
    verdict = orc.evaluate(game, [], "p0", legal)
    # X is worth more immediately (10) but p1 rejects it to hold out; the best response is Y.
    assert verdict.best == Propose((1,))
    assert verdict.value_of(Propose((1,))) > verdict.value_of(Propose((0,)))
    assert verdict.divergence(Propose((0,))) > 0


# --------------------------------------------------------------------------------------------------------- #
# 4. Equilibrium oracle: Okada divide-the-dollar recovers v = 1/n.
# --------------------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("n", [2, 3])
def test_equilibrium_okada_divide_the_dollar(n):
    tables = divide_the_dollar(n, steps=12)
    delta = 0.99
    sol = solve_equilibrium(tables, discount=delta, damping=0.5, max_iter=2000, tol=1e-10)
    assert sol.converged
    assert np.allclose(sol.values, 1.0 / n, atol=0.05)          # v_i -> 1/n
    cf = okada_closed_form(n, delta)
    # proposer 0's equilibrium proposal gives it approximately 1 - delta(n-1)/n
    share0 = float(tables.utility[sol.proposals[0], 0])
    assert share0 == pytest.approx(cf["proposer_keeps"], abs=0.12)


def test_equilibrium_oracle_on_game():
    game = _tiny_game()
    orc = EquilibriumOracle(discount=0.9)
    legal = [Propose((0,)), Propose((1,))]
    verdict = orc.evaluate(game, [], "p0", legal)
    assert verdict.best in legal
    assert set(verdict.action_values) == set(legal)


# --------------------------------------------------------------------------------------------------------- #
# 5. Faratin Boulware / Conceder concession curves.
# --------------------------------------------------------------------------------------------------------- #
def test_faratin_concession_curves():
    boul = TimeDependentPolicy.boulware(beta=0.2)
    conc = TimeDependentPolicy.conceder(beta=5.0)
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        assert boul.concession(t) == pytest.approx(t ** (1.0 / 0.2))
        assert conc.concession(t) == pytest.approx(t ** (1.0 / 5.0))
    # Boulware concedes far less than Conceder in the interior; both hit endpoints 0 and 1.
    assert boul.concession(0.5) < conc.concession(0.5)
    assert boul.concession(0.0) == pytest.approx(0.0)
    assert boul.concession(1.0) == pytest.approx(1.0)


# --------------------------------------------------------------------------------------------------------- #
# 6. PolicyParticipant round-trips a scripted mini-negotiation through a real Conversation.
# --------------------------------------------------------------------------------------------------------- #
def _accept_anything_game():
    """A 2-party game where every deal clears party 1's (zero) threshold, so party 1 accepts the first offer
    under AC_time(0)."""
    space = DealSpace((Issue("I", ("X", "Y", "Z")),))
    s0 = ScoreSheet("p0", ((5.0, 3.0, 1.0),), threshold=0.0)
    s1 = ScoreSheet("p1", ((1.0, 3.0, 5.0),), threshold=0.0)
    return GameSpec(space, (s0, s1), rounds=3, info="full", proposer=0, chat=False)


def test_policy_participant_round_trips_mini_negotiation():
    game = _accept_anything_game()
    tables = GameTables.from_game(game)
    proposer = PolicyParticipant("p0", TimeDependentPolicy.boulware(beta=0.2), seat=0, sheet=game.sheets[0],
                                 space=game.space, deadline=game.rounds, n_seats=2, tables=tables)
    accepter = PolicyParticipant("p1", TimeDependentPolicy(1.0, acceptance=ACTime(0.0)), seat=1,
                                 sheet=game.sheets[1], space=game.space, deadline=game.rounds, n_seats=2,
                                 tables=tables)
    conv = Conversation(participants=(proposer, accepter), shared_context="Negotiate one issue.",
                        communication=RoundRobinPolicy())
    conv.run(turns=2)

    msgs = [m for m in conv.transcript if m.author in ("p0", "p1")]
    assert msgs[0].author == "p0" and msgs[1].author == "p1"
    # the proposer emitted a parseable Propose; the accepter referenced its offer id and Accepted.
    a0 = parse_action(msgs[0].content)
    a1 = parse_action(msgs[1].content)
    assert a0.ok and isinstance(a0.action, Propose)
    assert a1.ok and isinstance(a1.action, Accept)
    assert a1.action.offer_id == "O1"            # the id the accepter derived for the standing offer
    # the emitted metadata carries the same typed action (round-trip through the message envelope)
    assert msgs[1].metadata["action"] == {"action": "accept", "offer_id": "O1"}


def test_policy_participant_raises_on_interp_request():
    game = _accept_anything_game()
    p = PolicyParticipant("p0", ToughPolicy(), seat=0, sheet=game.sheets[0], space=game.space,
                          deadline=game.rounds, n_seats=2)
    with pytest.raises(NotImplementedError):
        p.generate([{"role": "user", "content": "go"}], capture=object())


# --------------------------------------------------------------------------------------------------------- #
# 7. Integration: the composed Bayesian agent + oracle annotation on a generated game.
# --------------------------------------------------------------------------------------------------------- #
def test_bayesian_rational_policy_proposes_ir_deal():
    game = _accept_anything_game()
    tables = GameTables.from_game(game)
    pol = BayesianRationalPolicy(discount=0.9)
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=1, deadline=game.rounds,
                             tables=tables, opponents=(1,))
    action = pol(state)
    assert isinstance(action, (Propose, Accept, Walk))
    if isinstance(action, Propose):
        assert game.sheets[0].surplus(action.deal) >= 0     # never proposes below own threshold


def test_strategy_zoo_returns_valid_actions():
    from interlens.arena.negotiation.strategies import ZOO, NaiveTitForTatPolicy
    game = _accept_anything_game()
    tables = GameTables.from_game(game)
    # a state mid-negotiation: opponent has proposed its own best deal (Z), we hold one standing offer.
    state = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=2, deadline=game.rounds,
                             offers={"O1": (2,)}, standing="O1", received=[(2,)], my_offers=[(0,)],
                             tables=tables, opponents=(1,))
    policies = [make() for make in ZOO.values()] + [NaiveTitForTatPolicy()]
    for pol in policies:
        action = pol(state)
        assert isinstance(action, (Propose, Accept, Walk))
        if isinstance(action, Propose):
            assert game.sheets[0].surplus(action.deal) >= 0        # IR: never below own threshold


def test_bayesian_policy_shared_across_concurrent_seats_no_race():
    # Regression for the reported "dictionary changed size during iteration": one shared BayesianRationalPolicy
    # instance, called concurrently for multiple private-info seats, must not race on internal belief state.
    import concurrent.futures as cf
    sizes = (3, 3, 4)
    space = DealSpace(tuple(Issue(f"I{j}", tuple(f"o{k}" for k in range(s))) for j, s in enumerate(sizes)))
    sheets = [ScoreSheet(f"p{seat}", tuple(tuple(float(x) for x in
              np.random.default_rng(seat * 9 + j).integers(0, 10, s)) for j, s in enumerate(sizes)),
              threshold=6.0) for seat in range(3)]
    deals = space.deals()
    pol = BayesianRationalPolicy(discount=0.9)          # SHARED across seats (the hazard)

    def run(seat):
        received = [deals[(seat * 5 + k) % len(deals)] for k in range(4)]
        st = NegotiationState(seat=seat, sheet=sheets[seat], space=space, round=3, deadline=6,
                              offers={"P1": deals[2]}, standing="P1", received=received,
                              my_offers=[deals[1]], tables=None,
                              opponents=tuple(i for i in range(3) if i != seat), discount=0.9)
        return type(pol(st)).__name__

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        results = [f.result() for f in [ex.submit(run, i % 3) for i in range(120)]]   # re-raises thread errors
    assert all(r in ("Propose", "Accept", "Walk") for r in results)


def test_policy_reused_across_seats_no_utility_bleed():
    # One policy instance serving two seats must use each seat's OWN utilities (seat-aware cache), not the
    # first seat's cached column.
    space = DealSpace((Issue("I", ("X", "Y", "Z")),))
    s0 = ScoreSheet("p0", ((5.0, 3.0, 1.0),), threshold=0.0)   # argmax = X (index 0)
    s1 = ScoreSheet("p1", ((1.0, 3.0, 5.0),), threshold=0.0)   # argmax = Z (index 2)
    pol = ToughPolicy()
    a0 = pol(NegotiationState(seat=0, sheet=s0, space=space, deadline=4, opponents=(1,)))
    a1 = pol(NegotiationState(seat=1, sheet=s1, space=space, deadline=4, opponents=(0,)))
    assert a0.deal == (0,) and a1.deal == (2,)


def test_belief_separate_mode_reconstructs_distribution():
    true, alt1, alt2 = _three_types()
    # force the Hindriks-Tykhonov separate-learning factorization and check it yields a valid posterior.
    st = BeliefState(true.option_counts, types=[true, alt1, alt2], mode="separate", lam=1.0)
    for d in _concession_trace(true)[:5]:
        st.observe(d)
    post = st.posterior()
    assert post.shape == (3,)
    assert post.sum() == pytest.approx(1.0)
    assert np.all(post >= 0)


def test_exploitability_nonnegative():
    from interlens.arena.negotiation.bestresponse import exploitability
    game = _tiny_game()
    tables = GameTables.from_game(game)
    br = float(value_to_go_full_info(tables, [0, 1], T=2, discount=0.9)[1, 0])   # p0 best-response value
    # a revealed strategy that realizes less than the best response is exploitable (gap >= 0).
    gap = exploitability(tables, 0, revealed_value=br - 0.5, proposer_seq=[0, 1], T=2, discount=0.9)
    assert gap == pytest.approx(0.5)
    assert exploitability(tables, 0, revealed_value=br, proposer_seq=[0, 1], T=2, discount=0.9) == pytest.approx(0.0)


def test_oracles_read_game_discount():
    from interlens.arena.negotiation._oracle_common import effective_discount

    class G:                     # bare game-like object
        discount = 0.8
        breakdown_risk = 0.1

    class GDefault:
        pass

    assert effective_discount(G()) == pytest.approx(0.8 * 0.9)     # discount * (1 - breakdown_risk)
    assert effective_discount(G(), 0.5) == 0.5                     # explicit override wins
    assert effective_discount(GDefault()) == 1.0                   # neutral defaults

    # an oracle constructed WITHOUT an explicit discount reads the game's: two games with different discounts
    # produce different reservations (proof the game is the source of truth).
    space = DealSpace((Issue("I", ("X", "Y", "Z")),))
    s0 = ScoreSheet("p0", ((9.0, 5.0, 1.0),), threshold=0.0)
    s1 = ScoreSheet("p1", ((1.0, 5.0, 9.0),), threshold=0.0)
    g_hi = GameSpec(space, (s0, s1), rounds=6, discount=0.99, chat=False)
    g_lo = GameSpec(space, (s0, s1), rounds=6, discount=0.5, chat=False)
    orc = AcceptanceOracle(0)                                      # discount=None -> read from game
    r_hi = orc.evaluate(g_hi, [], "p0", [Walk()]).extra["reservation"]
    r_lo = orc.evaluate(g_lo, [], "p0", [Walk()]).extra["reservation"]
    assert r_hi > r_lo                                             # more patience -> higher reservation


def test_policy_vote_phase_accepts_ir_rejects_below_threshold():
    space = DealSpace((Issue("I", ("X", "Y", "Z")),))
    s0 = ScoreSheet("p0", ((5.0, 3.0, 1.0),), threshold=3.0)   # X surplus +2, Y surplus 0, Z surplus -2
    for pol in (ToughPolicy(), TimeDependentPolicy.boulware(beta=0.2), BayesianRationalPolicy()):
        # must_vote + IR standing offer -> Accept (no policy proposes in a vote-only phase)
        ir = NegotiationState(seat=0, sheet=s0, space=space, offers={"P2": (1,)}, standing="P2",
                              must_vote=True, opponents=(1,))
        assert pol(ir) == Accept("P2")
        # below-threshold standing offer -> Reject
        below = NegotiationState(seat=0, sheet=s0, space=space, offers={"P2": (2,)}, standing="P2",
                                 must_vote=True, opponents=(1,))
        assert pol(below) == Reject("P2")
        # no standing offer -> Walk
        none_st = NegotiationState(seat=0, sheet=s0, space=space, offers={}, standing=None, must_vote=True)
        assert isinstance(pol(none_st), Walk)


def test_policy_participant_reads_authoritative_state_block():
    game = _accept_anything_game()
    p = PolicyParticipant("p1", ToughPolicy(), seat=1, sheet=game.sheets[1], space=game.space,
                          deadline=game.rounds, n_seats=2)
    # a scenario-emitted authoritative state block: p0 has a standing offer O7 (deal Z), round 2.
    block = '```json\n{"negotiation_state": {"seat": 1, "round": 2, "deadline": 3, ' \
            '"offers": {"O7": [2]}, "standing": "O7", "received": [[2]], "my_offers": []}}\n```'
    state = p._state_from_view([{"role": "user", "content": block}])
    assert state.round == 2 and state.standing == "O7"
    assert state.offers["O7"] == (2,) and state.received == [(2,)]


def test_generated_game_oracle_annotation():
    from interlens.arena.negotiation.generate import generate_game
    game, _info = generate_game(n_parties=4, n_issues=4, seed=3)
    deals = game.space.deals()[:8]
    legal = [Propose(d) for d in deals] + [Walk()]
    agent = game.agents[0]
    for orc in (BestResponseOracle(0, discount=0.95), AcceptanceOracle(0, discount=0.95),
                EquilibriumOracle(discount=0.95)):
        verdict = orc.evaluate(game, [], agent, legal)
        # `best` is among the SCORED actions (which may be a superset of `legal`: the best-response oracle also
        # scores its own best-response proposal so a proposal turn's divergence is meaningful, even when the
        # scenario passes only the chosen propose in `legal`).
        assert verdict.best in verdict.action_values or verdict.best is None
        assert all(a in verdict.action_values for a in legal)   # every passed legal action is scored


def test_oracle_verdicts_are_json_serializable():
    # Regression: an inline oracle run must produce a JSON-serializable OracleVerdict (extra keyed by Action
    # objects / numpy arrays / OpponentType would crash the engine's episode save).
    import json
    from interlens.arena.negotiation.generate import generate_game
    from interlens.arena.negotiation.beliefs import BeliefOracle
    from interlens.arena.negotiation.acceptance import ThresholdOracle
    from interlens.arena.oracles import annotate
    game, _ = generate_game(n_parties=5, n_issues=5, seed=2)
    legal = [Propose(d) for d in game.space.deals()[:12]] + [Walk()]
    agent = game.agents[0]
    for orc in (BestResponseOracle(0), AcceptanceOracle(0), EquilibriumOracle(), ThresholdOracle(),
                BeliefOracle(0)):
        verdict = orc.evaluate(game, [], agent, legal)
        json.dumps(verdict.to_json())                       # must not raise
    recs = annotate([BestResponseOracle(0), AcceptanceOracle(0), EquilibriumOracle(), ThresholdOracle(),
                     BeliefOracle(0)], game, [], agent, legal, chosen_action=legal[0], round=1, seat=agent)
    json.dumps([r.to_json() for r in recs])                 # the full episode-record path
