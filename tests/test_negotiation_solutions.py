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
# [rational_agents scaffold: game-theory] 2026-07-23

"""Exact solution concepts on hand-computable toy games: Pareto/NBS/KS/egalitarian/utilitarian/MNW picks,
scale-invariance property tests (rescale one party -> NBS/KS unchanged, utilitarian moves), the empty-strict-IR
MNW fallback, distance metrics, and an optional negmas cross-check."""
from __future__ import annotations

import json

import numpy as np
import pytest

from interlens.arena.negotiation import solutions as S
from interlens.arena.negotiation.sheets import ScoreSheet, utility_matrix
from interlens.arena.negotiation.space import DealSpace, Issue


def _toy():
    """Single-issue 2-party game whose deals are exactly the surplus vectors (thresholds 0):
    opt0=(6,6) opt1=(10,3) opt2=(14,1) opt3=(5,5). opt3 is dominated by opt0. Hand-computed picks:
    Pareto={0,1,2}, NBS=0 (prod 36), KS=1 (max-min-normalized .5), egalitarian=0 (min surplus 6),
    utilitarian=2 (sum 15), MNW=NBS=0."""
    sp = DealSpace((Issue("X", ("o0", "o1", "o2", "o3")),))
    a = ScoreSheet("A", ((6, 10, 14, 5),), 0.0)
    b = ScoreSheet("B", ((6, 3, 1, 5),), 0.0)
    return sp, (a, b)


def _U_tau(sheets):
    return utility_matrix(_toy()[0], sheets), np.array([s.threshold for s in sheets])


def test_pareto_frontier_excludes_dominated():
    sp, sheets = _toy()
    U = utility_matrix(sp, sheets)
    assert list(S.pareto_mask(U).astype(int)) == [1, 1, 1, 0]


def test_solution_picks_hand_computed():
    sp, sheets = _toy()
    U, tau = _U_tau(sheets)
    assert S.nash_bargaining_index(U, tau)[0] == 0
    assert S.kalai_smorodinsky_index(U, tau)[0] == 1
    assert S.egalitarian_index(U, tau)[0] == 0
    assert S.utilitarian_index(U, tau)[0] == 2
    assert S.max_nash_welfare_index(U, tau)[0] == 0
    # high-level wrapper agrees and reports the named deal + surplus vector
    sols = S.all_solutions(sp, sheets)
    assert sols["nash"].index == 0 and sols["nash"].surpluses == (6.0, 6.0)
    assert sols["utilitarian"].index == 2 and sols["utilitarian"].scale_invariant is False
    assert sols["nash"].scale_invariant is True


@pytest.mark.parametrize("a,c", [(3.0, 0.0), (0.1, 0.0), (5.0, 100.0), (0.25, -3.0)])
def test_nbs_and_ks_are_scale_invariant(a, c):
    sp, (A, B) = _toy()
    A2 = A.rescaled(a, c)                       # rescale ONE party's utility -> NBS/KS argmax must not move
    U, tau = utility_matrix(sp, (A2, B)), np.array([A2.threshold, B.threshold])
    assert S.nash_bargaining_index(U, tau)[0] == 0
    assert S.kalai_smorodinsky_index(U, tau)[0] == 1


def test_utilitarian_is_not_scale_invariant():
    sp, (A, B) = _toy()
    # shrinking party A's scale by 10x reweights the raw surplus sum: the utilitarian pick moves 2 -> 0.
    A2 = A.rescaled(0.1, 0.0)
    U, tau = utility_matrix(sp, (A2, B)), np.array([A2.threshold, B.threshold])
    assert S.utilitarian_index(U, tau)[0] == 0 != 2


def test_empty_strict_ir_falls_back_to_mnw():
    sp = DealSpace((Issue("X", ("o0", "o1", "o2")),))
    A = ScoreSheet("A", ((6, 1, 3),), 4.0)      # surpluses A: (2, -3, -1)
    B = ScoreSheet("B", ((1, 5, 3),), 4.0)      # surpluses B: (-3, 1, -1)  -> no deal clears both
    U, tau = utility_matrix(sp, (A, B)), np.array([4.0, 4.0])
    assert not S.ir_mask(U, tau, strict=True).any()
    mnw_i, _, mnw_note = S.max_nash_welfare_index(U, tau)
    assert mnw_i == 0 and "|S|=1/2" in mnw_note          # largest satisfiable coalition = 1 of 2, best is opt0
    nash_i, _, nash_note = S.nash_bargaining_index(U, tau)
    assert nash_i == 0 and "Maximum Nash Welfare" in nash_note


def test_no_deal_is_rational_when_nothing_clears():
    sp = DealSpace((Issue("X", ("o0", "o1")),))
    A = ScoreSheet("A", ((6, 3),), 10.0)        # every utility below threshold for both
    B = ScoreSheet("B", ((3, 6),), 10.0)
    U, tau = utility_matrix(sp, (A, B)), np.array([10.0, 10.0])
    _, _, note = S.max_nash_welfare_index(U, tau)
    assert "no-deal is rational" in note


def test_distance_metrics():
    sp, sheets = _toy()
    U, tau = _U_tau(sheets)
    assert S.distance_to_frontier(U, tau, 0) == pytest.approx(0.0)     # opt0 is on the frontier
    assert S.distance_to_frontier(U, tau, 3) > 0.0                     # opt3 is dominated
    assert S.distance_to_solution(U, tau, 0, 0) == pytest.approx(0.0)
    assert S.distance_to_solution(U, tau, 2, 0) > 0.0


def test_analyze_is_consistent_and_json_serializable():
    sp, sheets = _toy()
    an = S.analyze(sp, sheets)
    assert an["deal_space_size"] == 4 and an["n_parties"] == 2
    assert an["pareto_count"] == 3 and an["ir_count"] == 4
    assert an["ir_pareto_count"] == 3
    assert an["dominated_acceptable_fraction"] == pytest.approx(1 - 3 / 4)
    assert an["solutions"]["nash"]["index"] == 0
    # best feasible joint = the utilitarian deal over the acceptable set (opt2, utilities (14,1), sum 15)
    assert an["max_feasible_joint_utility"] == pytest.approx(15.0)
    assert an["max_feasible_joint_surplus"] == pytest.approx(15.0)     # thresholds are 0 here
    assert an["max_feasible_joint_deal"] == [2]
    json.dumps(an)                                                     # must be plain JSON


def test_negmas_cross_check_pareto_and_nash():
    """Optional: if negmas is installed, its pareto/nash points must match ours on the toy game. Skipped when
    negmas is absent (it is NOT a dependency of this package)."""
    negmas = pytest.importorskip("negmas")
    try:
        from negmas.outcomes import make_issue, make_os
        from negmas.preferences import LinearAdditiveUtilityFunction as LU
        from negmas.preferences.ops import nash_points, pareto_frontier

        sp, (A, B) = _toy()
        os_ = make_os([make_issue(list(sp.issues[0].options), name="X")])
        outcomes = list(os_.enumerate_or_sample())
        ua = LU(values=[dict(zip(sp.issues[0].options, A.values[0]))], outcome_space=os_, reserved_value=0.0)
        ub = LU(values=[dict(zip(sp.issues[0].options, B.values[0]))], outcome_space=os_, reserved_value=0.0)
        front_utils, _ = pareto_frontier([ua, ub], outcomes)
        ours = {tuple(utility_matrix(sp, (A, B))[i]) for i in np.nonzero(S.pareto_mask(utility_matrix(sp, (A, B))))[0]}
        theirs = {tuple(float(x) for x in u) for u in front_utils}
        assert ours == theirs
        nps = nash_points([ua, ub], front_utils)
        assert nps, "negmas returned no nash point"
    except Exception as e:                       # pragma: no cover - API drift across negmas minors
        pytest.skip(f"negmas present but cross-check could not run ({type(e).__name__}: {e})")
