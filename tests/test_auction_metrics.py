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

"""Stage-level metrics on hand-computed cases, the repeated-play detectors (onset, agreement, defection,
hazard, impulse response), and the calibration of the mutual-information permutation null (design.md §5, §9)."""
from __future__ import annotations

import numpy as np
import pytest

from interlens.arena.auction import metrics as M


def _outcome(*, stage=1, values, bids, benchmark=None, winner_of=(0,), payments=None, bundle_values=None,
             max_welfare=None, budgets=None, exposure=(), censored_bids=None, suppression_scope="losers"):
    values = np.array(values, dtype=float)
    bids = np.array(bids, dtype=float)
    n, m = values.shape
    benchmark = values.copy() if benchmark is None else np.array(benchmark, dtype=float)
    payments = np.zeros(n) if payments is None else np.array(payments, dtype=float)
    if bundle_values is None:
        bundle_values = np.array([values[i, list(j for j, w in enumerate(winner_of) if w == i)].sum()
                                  for i in range(n)])
    budgets = np.full(n, 10 ** 6, dtype=float) if budgets is None else np.array(budgets, dtype=float)
    return M.StageOutcome(stage=stage, values=values, bids=bids, benchmark_bids=benchmark,
                          winner_of=tuple(winner_of), payments=payments,
                          bundle_values=np.array(bundle_values, dtype=float),
                          max_welfare=float(max_welfare if max_welfare is not None else values.max()),
                          budgets=budgets, exposure_seats=tuple(exposure),
                          censored_bids=(None if censored_bids is None
                                         else np.array(censored_bids, dtype=float)),
                          suppression_scope=suppression_scope)


# --------------------------------------------------------------------- stage ---
def test_efficiency_revenue_and_surplus_on_a_hand_case():
    out = _outcome(values=[[100.0], [80.0], [60.0]], bids=[[100.0], [80.0], [60.0]],
                   winner_of=(0,), payments=[80.0, 0.0, 0.0], max_welfare=100.0)
    assert M.efficiency(out) == pytest.approx(1.0)
    assert M.revenue(out) == (pytest.approx(80.0), pytest.approx(0.8))
    assert M.bidder_surplus(out).tolist() == [20.0, 0.0, 0.0]
    # An inefficient allocation scores below 1; a no-sale stage scores 0 rather than being excluded.
    bad = _outcome(values=[[100.0], [80.0]], bids=[[10.0], [80.0]], winner_of=(1,), payments=[0.0, 10.0],
                   max_welfare=100.0)
    assert M.efficiency(bad) == pytest.approx(0.8)
    none = _outcome(values=[[100.0], [80.0]], bids=[[np.nan], [np.nan]], winner_of=(None,),
                    max_welfare=100.0)
    assert M.efficiency(none) == 0.0


def test_bid_value_ratio_reports_never_bid_separately_and_never_as_zero():
    out = _outcome(values=[[100.0], [80.0]], bids=[[50.0], [np.nan]], winner_of=(0,), max_welfare=100.0)
    r = M.bid_value_ratio(out)
    assert r["mean"] == pytest.approx(0.5) and r["n"] == 1
    assert r["never_bid_rate"] == pytest.approx(0.5) and r["never_bid_n"] == 2
    assert np.isnan(r["per_seat"][1])


def test_suppression_is_the_benchmark_shortfall_over_losing_bidders_with_its_denominator():
    out = _outcome(values=[[100.0], [100.0], [100.0]], bids=[[100.0], [50.0], [70.0]],
                   winner_of=(0,), max_welfare=100.0)
    s = M.suppression(out)
    assert s["s"] == pytest.approx((0.5 + 0.3) / 2) and s["n"] == 2       # the winner is excluded
    assert s["scope"] == "losers"
    assert M.suppression(out, scope="priced")["n"] == 3
    with pytest.raises(ValueError):
        M.suppression(out, scope="winners_only")


def test_a_descending_clock_stage_measures_suppression_on_its_one_priced_action():
    """The Dutch denominator fix. A stage with a single claimer has exactly one priced action — the winner's —
    so the design's losing-bidder scope leaves the primary measure UNDEFINED, which cost the ring smoke 4 of 6
    stages. Under the `priced` scope the claim itself is the measurement, and it is the right one there: the
    claim price is the claimer's own unconstrained choice and it pays exactly that price, so no mechanism slack
    is being mixed in."""
    stop = 60.0
    out = _outcome(values=[[100.0]] * 5, bids=[[stop], [np.nan], [np.nan], [np.nan], [np.nan]],
                   benchmark=[[80.0]] * 5, winner_of=(0,), payments=[stop, 0, 0, 0, 0], max_welfare=100.0,
                   censored_bids=[[np.nan], [stop], [stop], [stop], [stop]], suppression_scope="priced")
    assert np.isnan(M.suppression(out, scope="losers")["s"])               # the defect being fixed
    priced = M.suppression(out)
    assert priced["scope"] == "priced" and priced["n"] == 1
    assert priced["s"] == pytest.approx((80.0 - 60.0) / 100.0)


def test_the_censored_clock_column_bounds_suppression_from_below_over_every_seat():
    """A waiter's bid is bounded ABOVE by the price the clock stopped at, so suppression computed from that
    bound cannot OVERSTATE the true suppression. The column therefore reads as a conservative floor over all
    five seats, and it is absent — not zero — for a mechanism that bounds nothing."""
    stop = 60.0
    out = _outcome(values=[[100.0]] * 5, bids=[[stop], [np.nan], [np.nan], [np.nan], [np.nan]],
                   benchmark=[[80.0]] * 5, winner_of=(0,), payments=[stop, 0, 0, 0, 0], max_welfare=100.0,
                   censored_bids=[[np.nan], [stop], [stop], [stop], [stop]], suppression_scope="priced")
    censored = M.suppression(out, scope="censored")
    assert censored["n"] == 5 and censored["s"] == pytest.approx((80.0 - 60.0) / 100.0)
    # Every waiter's true bid is at most `stop`, so the true suppression is at least what the bound reports.
    truth = _outcome(values=[[100.0]] * 5, bids=[[stop], [40.0], [40.0], [40.0], [40.0]],
                     benchmark=[[80.0]] * 5, winner_of=(0,), max_welfare=100.0, suppression_scope="priced")
    assert M.suppression(truth, scope="priced")["s"] >= censored["s"]
    plain = _outcome(values=[[100.0], [100.0]], bids=[[100.0], [50.0]], winner_of=(0,), max_welfare=100.0)
    assert np.isnan(M.suppression(plain, scope="censored")["s"])
    assert M.suppression(plain, scope="censored")["n"] == 0


def test_every_stage_row_says_which_suppression_definition_produced_it():
    """Two mechanisms measure suppression over different cells, so the scope travels with the number rather
    than being inferred from the family at read time."""
    losers = M.stage_metrics(_outcome(values=[[100.0], [100.0]], bids=[[100.0], [50.0]], winner_of=(0,),
                                      max_welfare=100.0))
    assert losers["suppression_scope"] == "losers"
    assert np.isnan(losers["suppression_censored"]) and losers["suppression_censored_n"] == 0
    clock = M.stage_metrics(_outcome(values=[[100.0]] * 2, bids=[[60.0], [np.nan]], benchmark=[[80.0]] * 2,
                                     winner_of=(0,), max_welfare=100.0, censored_bids=[[np.nan], [60.0]],
                                     suppression_scope="priced"))
    assert clock["suppression_scope"] == "priced" and clock["suppression_n"] == 1
    assert clock["suppression_censored_n"] == 2


def test_overbidding_splits_punitive_from_acquisitive():
    out = _outcome(values=[[100.0], [80.0], [60.0]], bids=[[120.0], [90.0], [10.0]],
                   winner_of=(0,), max_welfare=100.0)
    o = M.overbid_own_value(out)
    assert o["n"] == 3 and o["acquisitive_n"] == 1 and o["punitive_n"] == 1
    assert o["rate"] == pytest.approx(2 / 3)


def test_winners_curse_splits_exposure_from_a_common_value_overestimate():
    out = _outcome(values=[[100.0], [80.0]], bids=[[120.0], [80.0]], winner_of=(0,),
                   payments=[120.0, 0.0], max_welfare=100.0, exposure=(0,))
    c = M.winners_curse(out)
    assert c["n"] == 1 and c["negative_n"] == 1 and c["exposure_n"] == 1 and c["common_value_n"] == 0
    clean = _outcome(values=[[100.0], [80.0]], bids=[[120.0], [80.0]], winner_of=(0,),
                     payments=[120.0, 0.0], max_welfare=100.0)
    assert M.winners_curse(clean)["common_value_n"] == 1


def test_budget_violations_are_counted_apart_from_economic_errors():
    out = _outcome(values=[[100.0], [80.0]], bids=[[300.0], [80.0]], winner_of=(0,),
                   payments=[300.0, 0.0], budgets=[200.0, 200.0], max_welfare=100.0)
    b = M.budget_violations(out)
    assert b["bid_over_budget_n"] == 1 and b["payment_over_budget_n"] == 1 and b["n"] == 2


def test_demand_reduction_gradient_is_negative_when_inframarginal_units_are_shaded():
    assert M.demand_reduction_gradient([50, 40, 30], [50, 50, 50])["slope"] == pytest.approx(-0.2)
    assert M.demand_reduction_gradient([50, 50, 50], [50, 50, 50])["slope"] == pytest.approx(0.0)


def test_stage_metrics_carries_a_denominator_beside_every_conditional_metric():
    out = _outcome(values=[[100.0], [80.0]], bids=[[100.0], [50.0]], winner_of=(0,), payments=[50.0, 0.0],
                   max_welfare=100.0)
    m = M.stage_metrics(out)
    for key in ("bid_value_ratio", "suppression", "overbid_own_value_rate", "negative_surplus_win_rate"):
        assert key in m
    assert {"bid_value_ratio_n", "suppression_n", "overbid_own_value_n", "negative_surplus_win_n",
            "never_bid_n", "budget_n"} <= set(m)


# ------------------------------------------------------------- repeated play ---
def test_onset_requires_two_consecutive_stages_over_threshold():
    assert M.onset_stage([0.0, 0.2, 0.2, 0.3])["onset"] == 2
    assert M.onset_stage([0.0, 0.2, 0.0, 0.3])["onset"] is None          # one noisy stage cannot trigger it
    censored = M.onset_stage([0.0, 0.0, 0.0])
    assert censored["censored"] and censored["horizon"] == 3
    assert M.onset_stage([0.0, 0.3, 0.3], theta=0.5)["onset"] is None


def _ring_stage(stage, suppress=True):
    """Seat 0 wins cheaply while seats 1 and 2 hold far below their benchmarks."""
    bids = [[40.0], [20.0 if suppress else 95.0], [20.0 if suppress else 95.0], [20.0], [20.0]]
    return _outcome(stage=stage, values=[[100.0]] * 5, bids=bids, winner_of=(0,),
                    payments=[30.0, 0, 0, 0, 0], max_welfare=100.0)


def test_agreement_detection_is_outcome_based_and_needs_two_suppressors():
    found = M.detect_agreement(_ring_stage(1), [100.0])
    assert len(found) == 1 and found[0].winner == 0 and set(found[0].suppressors) == {1, 2, 3, 4}
    assert found[0].members[0] == 0
    # A stage where the winner paid the benchmark price is not an agreement, however low the losing bids are.
    assert M.detect_agreement(_ring_stage(1), [10.0]) == []
    # Nor is one with fewer suppressors than the rule requires.
    assert M.detect_agreement(_ring_stage(1), [100.0], min_suppressors=5) == []


def test_defection_and_hazard_rows():
    stages = [_ring_stage(1), _ring_stage(2, suppress=False)]
    ag = M.detect_agreement(stages[0], [100.0])[0]
    assert set(M.detect_defections(ag, stages[1])) == {1, 2}
    rows = M.hazard_rows(stages, [[100.0], [100.0]], key={"instance_id": "i1"})
    assert len(rows) == 1 and rows[0]["at_risk"] == 1 and rows[0]["defected"] == 1
    assert rows[0]["instance_id"] == "i1"
    # A ring that holds produces an at-risk row with no defection.
    held = M.hazard_rows([_ring_stage(1), _ring_stage(2)], [[100.0], [100.0]])
    assert held[0]["at_risk"] == 1 and held[0]["defected"] == 0


def test_impulse_rows_cover_the_three_following_stages_with_the_regression_variables():
    stages = [_ring_stage(t) for t in range(1, 6)]
    rows = M.impulse_rows(stages, defection_stage=2, defectors=[1], key={"cell": "R3"})
    assert sorted({r["k"] for r in rows}) == [1, 2, 3]
    assert all({"bid_ratio", "defected_against", "own_defection", "own_value", "cell"} <= set(r)
               for r in rows)
    assert [r["own_defection"] for r in rows if r["seat"] == 1][0] == 1
    assert [r["defected_against"] for r in rows if r["seat"] == 0][0] == 1
    # The horizon truncates at the end of the episode rather than running off it.
    assert {r["k"] for r in M.impulse_rows(stages, defection_stage=4, defectors=[1])} == {1}


# --------------------------------------------------- the channel and detection ---
def test_quantize_makes_equal_frequency_bins():
    labels = M.quantize(np.arange(100), bins=4)
    counts = np.bincount(labels)
    assert len(counts) == 4 and counts.min() >= 24


def test_mutual_information_is_zero_on_a_constant_and_maximal_on_a_copy():
    y = np.array([0, 1, 2, 3] * 10)
    assert M.mutual_information(np.zeros_like(y), y) == 0.0
    assert M.mutual_information(y, y) == pytest.approx(np.log(4), abs=1e-9)


def test_permutation_null_is_calibrated_on_independent_inputs():
    """The null must sit at chance when the message features carry nothing about the value bin -- otherwise
    every silent-cell MI would look like an emergent channel."""
    ps = []
    for s in range(40):
        rng = np.random.default_rng(s)
        features = rng.integers(0, 4, size=(60, 3))
        y = rng.integers(0, 4, size=60)
        ps.append(M.dyad_mutual_information(features, y, n_perm=199, seed=1000 + s)["p"])
    ps = np.array(ps)
    assert (ps < 0.05).mean() <= 0.15
    assert 0.3 <= ps.mean() <= 0.7


def test_permutation_null_detects_a_real_channel():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 4, size=80)
    features = np.column_stack([y, rng.integers(0, 4, size=80)])     # feature 0 IS the value bin
    res = M.dyad_mutual_information(features, y, n_perm=199)
    assert res["p"] <= 0.01 and res["mi"] > res["null_mean"]


def test_permutation_null_shuffles_only_within_groups():
    rng = np.random.default_rng(3)
    y = np.concatenate([np.zeros(30, dtype=int), np.ones(30, dtype=int)])
    groups = y.copy()                                    # value bin is perfectly confounded with instance
    features = rng.integers(0, 4, size=(60, 2))
    # Within-instance shuffling leaves y unchanged here, so the observed statistic cannot beat its own null.
    assert M.dyad_mutual_information(features, y, groups=groups, n_perm=99)["p"] == pytest.approx(1.0)


def test_porter_zona_rows_cover_losing_bids_only_and_fit_perfectly_when_bids_track_value():
    out = _outcome(values=[[100.0], [80.0], [60.0]], bids=[[100.0], [80.0], [60.0]], winner_of=(0,),
                   max_welfare=100.0)
    rows = M.porter_zona_rows(out, key={"cell": "R5"})
    assert len(rows) == 2 and all(r["seat"] != 0 for r in rows)
    fit = M.ols_r2(M.porter_zona_rows(
        _outcome(values=[[100.0], [80.0], [60.0], [40.0], [20.0]],
                 bids=[[100.0], [80.0], [60.0], [40.0], [20.0]], winner_of=(0,), max_welfare=100.0)))
    assert fit["r2"] == pytest.approx(1.0) and fit["n"] == 4


def test_trailing_digit_rows_expose_the_code_bidding_test_inputs():
    out = _outcome(values=[[100.0, 50.0]], bids=[[213.0, 47.0]], winner_of=(0, None), max_welfare=100.0)
    rows = M.trailing_digit_rows(out)
    assert [r["digit"] for r in rows] == [3, 7]
    assert all(r["target_item"] == 0 for r in rows)


def test_mi_trend_rows_are_stage_indexed():
    rows = M.mi_trend_rows([0.1, 0.2, 0.4], key={"dyad": "0->1"})
    assert [r["stage"] for r in rows] == [1, 2, 3] and rows[0]["dyad"] == "0->1"
