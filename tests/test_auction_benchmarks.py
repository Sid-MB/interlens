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

"""The per-stage equilibrium benchmarks: the closed forms on hand cases, the numerical first-price solution
against its analytic answer, the SAA straightforward-bidding simulation, and the winner's-curse correction.

Every suppression number in the campaign divides against these, so each one is checked against an
independently-known value rather than against itself."""
from __future__ import annotations

import numpy as np
import pytest

from interlens.arena.auction import benchmarks as B
from interlens.arena.auction.allocation import ValueModel
from interlens.arena.auction.spec import Mechanism, generate_spec


def test_truthful_benchmark_bids_value_and_prices_at_the_second_highest():
    vm = ValueModel(values=np.array([[10], [7], [3]]), capacities=(1, 1, 1), decays=(1.0, 1.0, 1.0),
                    synergy_rates=(0.0,) * 3, synergy_targets=(None,) * 3)
    bench = B.truthful_benchmark(vm, tie_break=(0, 1, 2))
    assert bench.bids.ravel().tolist() == [10.0, 7.0, 3.0]
    assert bench.alloc.winner_of == (0,) and bench.revenue == pytest.approx(7.0)
    assert bench.welfare == pytest.approx(10.0)


def test_rnne_closed_form_is_the_n_minus_one_over_n_rule():
    assert B.rnne_shade(5) == pytest.approx(0.8)
    assert B.rnne_symmetric_bid(100.0, 5) == pytest.approx(80.0)


@pytest.mark.parametrize("value", [0.3, 0.6, 0.9])
def test_numeric_first_price_solution_reproduces_the_uniform_closed_form(value):
    # Four rivals with iid U[0, 1] values: the exact symmetric equilibrium is (n-1)/n * v = 0.8 v at n = 5.
    grid = np.linspace(0.0, 1.0, 2001)
    pmf = (grid, np.ones_like(grid) / grid.size)
    got = B.rnne_bid_against(value, [pmf] * 4, lower=0.0, n_grid=800)
    assert got == pytest.approx(0.8 * value, abs=2e-3)


def test_numeric_first_price_bid_is_below_value_and_monotone_on_a_real_stage():
    spec = generate_spec(11, mechanism=Mechanism.dutch(), value_structure="apv", horizon=1)
    bench = B.stage_benchmark(spec, 1)
    values = np.array([v[0] for v in spec.stage(1).values], dtype=float)
    bids = bench.bids.ravel()
    assert np.all(bids <= values + 1e-9)
    order = np.argsort(values)
    assert np.all(np.diff(bids[order]) >= -1e-9)          # higher value never bids less
    assert bench.label == "rnne_numeric"


def test_ipv_dutch_benchmark_uses_the_closed_form():
    spec = generate_spec(11, mechanism=Mechanism.dutch(), value_structure="ipv", horizon=1)
    bench = B.stage_benchmark(spec, 1)
    values = np.array([v[0] for v in spec.stage(1).values], dtype=float)
    assert bench.label == "rnne_closed_form"
    assert np.allclose(bench.bids.ravel(), 0.8 * values)


def test_saa_straightforward_bidding_awards_lots_to_their_highest_valuers():
    # Seats 0 and 1 both chase lot 0; only seat 2 wants lot 1, and each seat may hold one lot.
    vm = ValueModel(values=np.array([[100, 1], [90, 1], [1, 40]]), capacities=(1, 1, 1),
                    decays=(1.0,) * 3, synergy_rates=(0.0,) * 3, synergy_targets=(None,) * 3)
    bench = B.saa_competitive_benchmark(vm, increment=5, tie_break=(0, 1, 2))
    assert bench.alloc.winner_of == (0, 2)
    # The contested lot clears within one increment of the highest losing value (the loser stops bidding at
    # the first price where its surplus would be non-positive); the uncontested one at one increment.
    assert 85 <= bench.prices[0] <= 90
    assert bench.prices[1] == 5
    # The PRIMARY benchmark bid is information-conditional: the amount a straightforward bidder actually
    # SUBMITS on the lots it demands, and nan on the lots it never demands. Scoring the undemanded cells
    # against own value booked a capacity constraint as suppression, and scoring the demanded ones against own
    # value booked the price path as suppression. The all-lots own-value matrix is the secondary column.
    assert np.isnan(bench.bids[0, 1]) and np.isnan(bench.bids[2, 0])
    assert bench.bids[0, 0] == bench.prices[0]          # the winner's last submitted amount is the price
    assert bench.bids[1, 0] == bench.prices[0] - 5      # the loser's is the increment below, where it stopped
    assert bench.bids[2, 1] == bench.prices[1]
    assert bench.detail["truthful_bids"].tolist() == vm.values.astype(float).tolist()
    assert bench.detail["demanded"] == [[0], [0], [1]]


def test_onpath_benchmark_prices_demand_at_the_prices_the_round_actually_showed():
    """The suppression denominator for the SAA family (design.md §6): demand recomputed on the REALIZED path.

    Two rounds of a hand-built trajectory, so the expected numbers are known independently of any simulation.
    Seats 0 and 1 both want lot 0; seat 2 wants lot 1 only."""
    vm = ValueModel(values=np.array([[100, 1], [90, 1], [1, 40]]), capacities=(1, 1, 1),
                    decays=(1.0,) * 3, synergy_rates=(0.0,) * 3, synergy_targets=(None,) * 3)
    trajectory = [
        {"round": 1, "prices": [0.0, 0.0], "holders": [None, None]},
        {"round": 2, "prices": [5.0, 5.0], "holders": [0, 2]},
    ]
    bench = B.saa_onpath_benchmark(vm, trajectory=trajectory, increment=5)
    assert bench.label == "straightforward_onpath"
    # Round 1: everyone demands at reserve + increment = 5. Round 2: seat 1 is still under its value and
    # raises to 10; seat 0 already holds lot 0 and re-demands it at the standing 5, so its recorded amount
    # stays 5; seat 2 holds lot 1 likewise.
    assert bench.bids[1, 0] == 10
    assert bench.bids[0, 0] == 5
    assert bench.bids[2, 1] == 5
    # Never-demanded cells stay nan — a capacity- or value-constrained seat placed no priced action there,
    # and scoring those cells would book a constraint as suppression.
    assert np.isnan(bench.bids[0, 1]) and np.isnan(bench.bids[2, 0])
    # An on-path demand has no counterfactual outcome; those live on the independent clock instead.
    assert np.isnan(bench.revenue) and np.isnan(bench.welfare)


def test_onpath_benchmark_drops_lots_the_budget_cannot_pay_for():
    """A payment has to be collectible, so the benchmark never credits a seat with a bid it could not submit.
    Lots are dropped in ascending surplus order, keeping the most valuable part of the demand."""
    vm = ValueModel(values=np.array([[100, 90]]), capacities=(2,), decays=(1.0,),
                    synergy_rates=(0.0,), synergy_targets=(None,))
    trajectory = [{"round": 1, "prices": [0.0, 0.0], "holders": [None, None]}]
    rich = B.saa_onpath_benchmark(vm, trajectory=trajectory, increment=10, budgets=(1000,))
    assert rich.bids[0, 0] == 10 and rich.bids[0, 1] == 10
    poor = B.saa_onpath_benchmark(vm, trajectory=trajectory, increment=10, budgets=(10,))
    assert poor.bids[0, 0] == 10                       # the higher-surplus lot is kept
    assert np.isnan(poor.bids[0, 1])                   # the second is unaffordable and simply not demanded


def test_stage_benchmark_dispatches_onpath_for_saa_and_carries_the_independent_clock_beside_it():
    """Both forms coexist: on-path is the returned bid benchmark, the independent clock rides in detail as a
    descriptive revenue/efficiency ceiling and must never become the suppression denominator."""
    spec = generate_spec(6, mechanism=Mechanism.saa(4), value_structure="apv", horizon=1)
    trajectory = [{"round": 1,
                   "prices": [float(spec.mechanism.reserve)] * spec.n_items,
                   "holders": [None] * spec.n_items}]
    onpath = B.stage_benchmark(spec, 1, trajectory=trajectory)
    assert onpath.label == "straightforward_onpath"
    independent = onpath.detail["independent_clock"]
    assert independent["label"] == "straightforward"
    assert np.isfinite(independent["revenue"]) and np.isfinite(independent["welfare"])
    # Without a trajectory the dispatcher still returns the independent simulation, so the sealed/one-shot
    # path and any off-line caller are unchanged.
    assert B.stage_benchmark(spec, 1).label == "straightforward"


def test_best_bundle_at_prices_respects_capacity_and_synergy():
    vm = ValueModel(values=np.array([[6, 6, 1]]), capacities=(2,), decays=(1.0,), synergy_rates=(1.0,),
                    synergy_targets=((0, 1),))
    bundle, surplus = B.best_bundle_at_prices(vm, 0, np.array([5.0, 5.0, 0.0]))
    assert bundle == (0, 1) and surplus == pytest.approx(6 + 6 + 12 - 10)


def test_uniform_and_clinching_benchmarks_use_true_marginal_values():
    vm = ValueModel(values=np.array([[10], [8], [4]]), capacities=(2, 1, 1), decays=(0.5, 1.0, 1.0),
                    synergy_rates=(0.0,) * 3, synergy_targets=(None,) * 3)
    assert B.marginal_value_schedule(vm, 0, 3).tolist() == [10.0, 5.0, 0.0]
    up = B.uniform_price_benchmark(vm, n_units=2, tie_break=(0, 1, 2))
    assert up.label == "demand_reduction_free" and "not the uniform-price" in up.note
    cl = B.clinching_benchmark(vm, n_units=2)
    assert cl.label == "truthful_demand" and cl.detail["units"][0] >= 1


def test_winners_curse_correction_shades_strictly_below_the_naive_signal():
    grid = np.arange(40, 121, dtype=float)
    naive = 100.0 + 0.45 * 90
    corrected = B.expected_value_given_winning(90, private_part=100.0, gamma=0.45, sigma_nu=0.30,
                                               n_rivals=4, resale_grid=grid)
    assert corrected < naive
    # More rivals means a stronger curse, and no noise means no correction at all.
    stronger = B.expected_value_given_winning(90, private_part=100.0, gamma=0.45, sigma_nu=0.30,
                                              n_rivals=8, resale_grid=grid)
    assert stronger < corrected
    assert B.expected_value_given_winning(90, private_part=100.0, gamma=0.45, sigma_nu=0.0,
                                          n_rivals=4, resale_grid=grid) == pytest.approx(naive)


def test_stage_benchmark_dispatches_on_every_committed_family():
    cases = {
        "sealed_single": (Mechanism.sealed(), "apv"),
        "english": (Mechanism.english(), "apv"),
        "dutch": (Mechanism.dutch(), "ipv"),
        "saa": (Mechanism.saa(3), "apv"),
        "uniform_price": (Mechanism.uniform_price(3), "apv"),
        "clinching": (Mechanism.clinching(3), "apv"),
    }
    for family, (mech, structure) in cases.items():
        spec = generate_spec(7, mechanism=mech, value_structure=structure, horizon=1)
        bench = B.stage_benchmark(spec, 1)
        assert bench.citation_key and bench.bids.shape[0] == spec.n_bidders, family
