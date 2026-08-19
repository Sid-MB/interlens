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

# [implement: pure-arm rounds sweep] 2026-08-17
"""The equivalences the long-horizon solver optimizations rest on.

Each optimization replaced "recompute per item" with "compute once and reuse". None of them may change a
number, so each gets a test that pins the fast path against the slow one it replaced — batched vote valuation
against the per-offer call, the cached belief replay against a from-scratch fold, the vectorized acceptance
weights against the per-deal callable, and the memoized action key against a direct serialization.
"""
from __future__ import annotations

import numpy as np
import pytest

from interlens.arena.actions import Accept, Propose, Reject, Walk, action_key
from interlens.arena.negotiation.acceptance import AcceptanceOracle, offer_surplus_pmf
from interlens.arena.negotiation.beliefs import (BeliefState, clear_replay_cache, replay_belief)
from interlens.arena.negotiation.bestresponse import (conditional_vote_values,
                                                      conditional_vote_values_batch, passage_probability,
                                                      value_to_go_beliefs)
from interlens.arena.negotiation.oracle_context import GameTables
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet
from interlens.arena.negotiation.space import DealSpace, Issue


def game(n_seats: int = 5) -> GameSpec:
    space = DealSpace((Issue("Power", ("A", "B", "C")), Issue("Cooling", ("X", "Y", "Z"))))
    sheets = tuple(ScoreSheet(f"P{i}", ((9.0 - 2 * i, 4.0, 1.0 + i), (0.0, 5.0 + i, 2.0)), 5.0)
                   for i in range(n_seats))
    return GameSpec(space, sheets, rounds=6, info="private", chat=True, proposer=0, discount=0.95)


def posterior_table(tables: GameTables, seed: int = 0) -> np.ndarray:
    """A dense, non-degenerate ``(D, n)`` acceptance table — deliberately not 0/1, so a batching bug that
    happens to be invisible on deterministic full-information votes still shows up here."""
    rng = np.random.default_rng(seed)
    return rng.uniform(0.05, 0.95, size=(tables.n_deals, tables.n_agents))


# --- batched vote valuation == the per-offer call ---------------------------------------------------------

@pytest.mark.parametrize("min_accept", [None, 3, 4])
def test_batched_vote_values_match_the_per_offer_call_exactly(min_accept):
    tables = GameTables.from_game(game())
    ap = posterior_table(tables)
    idx = [0, 5, 8, 3, 1]
    proposers = [1, 2, None, 1, 4]
    forced_yes = [(), (2,), (), (3, 4), ()]
    forced_no = [(), (), (4,), (), (1,)]
    surpluses = [float(tables.surplus[d, 0]) for d in idx]
    batch = conditional_vote_values_batch(ap, proposers, 0, idx, surpluses, 0.25,
                                          min_accept=min_accept, forced_yes=forced_yes, forced_no=forced_no)
    for k in range(len(idx)):
        one = conditional_vote_values(ap, proposers[k], 0, idx[k], surpluses[k], 0.25,
                                      min_accept=min_accept, forced_yes=forced_yes[k], forced_no=forced_no[k])
        assert [float(col[k]) for col in batch] == list(one)      # bitwise, not approx


def test_batched_vote_values_handle_an_empty_request():
    tables = GameTables.from_game(game())
    out = conditional_vote_values_batch(posterior_table(tables), [], 0, [], [], 0.5)
    assert all(len(col) == 0 for col in out)


def test_passage_probability_rows_are_independent():
    """The property every batching step above relies on: solving a row inside a stack gives the same float64
    as solving it alone."""
    tables = GameTables.from_game(game())
    ap = posterior_table(tables, seed=3)
    full = passage_probability(ap, 2, min_accept=4)
    for d in (0, 4, 8):
        assert float(passage_probability(ap[d:d + 1], 2, min_accept=4)[0]) == float(full[d])


# --- cached belief replay == a from-scratch fold ----------------------------------------------------------

def test_cached_replay_matches_a_fresh_replay_at_every_prefix():
    counts = (3, 3)
    offers = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (0, 2)]
    clear_replay_cache()
    for k in range(len(offers) + 1):
        fresh = BeliefState(counts)
        for deal in offers[:k]:
            fresh.observe(deal)
        cached = replay_belief(counts, offers[:k])
        assert np.array_equal(cached.posterior(), fresh.posterior())
        assert cached._last == fresh._last
        assert cached.frequency_utility((1, 1)) == fresh.frequency_utility((1, 1))


def test_a_warm_cache_still_matches_and_the_copy_is_private():
    counts = (3, 3)
    offers = [(0, 0), (1, 0), (1, 1)]
    clear_replay_cache()
    first = replay_belief(counts, offers)          # cold: folds everything
    second = replay_belief(counts, offers)         # warm: pure cache hit
    assert np.array_equal(first.posterior(), second.posterior())
    second.observe((2, 2))                          # mutating what we were handed...
    third = replay_belief(counts, offers)
    assert np.array_equal(first.posterior(), third.posterior())   # ...cannot corrupt the cache
    clear_replay_cache()
    assert np.array_equal(replay_belief(counts, offers).posterior(), first.posterior())


def test_an_explicit_type_grid_bypasses_the_cache_and_still_folds():
    from interlens.arena.negotiation.beliefs import build_type_grid
    counts = (3, 3)
    grid = build_type_grid(counts, tau_levels=(0.4,), max_rankings=2)
    offers = [(0, 0), (2, 2)]
    fresh = BeliefState(counts, types=grid)
    for deal in offers:
        fresh.observe(deal)
    assert np.array_equal(replay_belief(counts, offers, types=grid).posterior(), fresh.posterior())


# --- vectorized acceptance weights == the per-deal callable ------------------------------------------------

def test_accept_weights_reproduce_the_per_deal_callable():
    tables = GameTables.from_game(game())
    ap = posterior_table(tables, seed=7)
    vec = passage_probability(ap, 0, min_accept=None)

    def acc_fn(deal):
        row = tables.index[tuple(int(x) for x in deal)]
        return float(passage_probability(ap[row:row + 1], 0, min_accept=None)[0])

    by_fn = offer_surplus_pmf(tables, 0, acc_fn)
    by_vec = offer_surplus_pmf(tables, 0, accept_weights=vec)
    assert np.array_equal(by_fn[0], by_vec[0]) and np.array_equal(by_fn[1], by_vec[1])
    # and through the oracle, which is how the policy reaches it
    assert AcceptanceOracle(0, discount=0.95, accept_prob_fn=acc_fn).reservation(tables, 5) == \
        AcceptanceOracle(0, discount=0.95, accept_prob_vec=vec).reservation(tables, 5)


def test_accept_weights_reject_a_wrong_length_vector():
    tables = GameTables.from_game(game())
    with pytest.raises(ValueError, match="accept_weights"):
        offer_surplus_pmf(tables, 0, accept_weights=np.ones(3))


def test_accept_weights_are_not_mutated_by_the_filters():
    tables = GameTables.from_game(game())
    vec = posterior_table(tables, seed=1)[:, 0]
    before = vec.copy()
    offer_surplus_pmf(tables, 0, accept_weights=vec)
    assert np.array_equal(vec, before)


# --- the memoized backward induction ----------------------------------------------------------------------

def test_belief_value_to_go_is_unchanged_by_memoizing_the_passage_probabilities():
    """``value_to_go_beliefs`` now solves each distinct proposer once instead of once per round. Recomputing
    the recursion by hand here pins that the memo returns the same curve."""
    tables = GameTables.from_game(game())
    ap = posterior_table(tables, seed=11)
    opp = {p: (p * 7) % tables.n_deals for p in range(1, 5)}
    seq = [0, 1, 2, 3, 4]
    Vi = value_to_go_beliefs(tables, 0, seq, 9, 0.9, ap, opp, min_accept=4)

    S = tables.surplus[:, 0]
    expect = np.zeros(11)
    for t in range(9, 0, -1):
        p = seq[(t - 1) % 5]
        cont = 0.9 * expect[t + 1]
        if p == 0:
            q = passage_probability(ap, 0, min_accept=4)
            expect[t] = max(float((q * S + (1.0 - q) * cont).max()), cont)
        else:
            d = opp[p]
            yes = np.array(ap[d:d + 1], copy=True)
            no = np.array(yes, copy=True)
            yes[0, 0], no[0, 0] = 1.0, 0.0
            qy = float(passage_probability(yes, p, min_accept=4)[0])
            qn = float(passage_probability(no, p, min_accept=4)[0])
            expect[t] = max(qy * float(S[d]) + (1.0 - qy) * cont, qn * float(S[d]) + (1.0 - qn) * cont)
    assert np.array_equal(Vi, expect)


# --- the memoized action key ------------------------------------------------------------------------------

def test_action_key_is_unchanged_by_memoization_including_unhashable_actions():
    import json
    for action in (None, Walk(), Accept("O3"), Reject("O3"), Propose((0, 1))):
        expect = None if action is None else json.dumps(action.to_json(), sort_keys=True)
        assert action_key(action) == expect
        assert action_key(action) == expect        # second call comes from the cache
    # a Propose holding a list is unhashable; it must still serialize rather than raise
    assert action_key(Propose([0, 1])) == action_key(Propose((0, 1)))
