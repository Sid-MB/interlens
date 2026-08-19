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
"""``arena.negotiation.belief_accuracy``: the nearest-type mapping onto the opponent-type grid, the three
scores against a known posterior, and the learning behaviour on an informative concession sequence."""
from __future__ import annotations

import numpy as np
import pytest

from interlens.arena.negotiation import belief_accuracy as ba
from interlens.arena.negotiation.beliefs import BeliefState
from interlens.arena.negotiation.oracle_context import deal_list, issue_sizes
from interlens.arena.negotiation.sheets import ScoreSheet
from interlens.arena.negotiation.space import DealSpace, Issue


SPACE = DealSpace((Issue("Power", ("A", "B", "C")), Issue("Cooling", ("X", "Y"))))
DEALS = np.asarray(deal_list(SPACE), dtype=int)
OPTION_COUNTS = issue_sizes(SPACE)


def on_grid_sheet(threshold: float = 0.55) -> ScoreSheet:
    """A sheet lying EXACTLY on the default grid: weights (2/3, 1/3) — the first two-issue ranking profile —
    with an uphill 3-option evaluator and a downhill 2-option one, so its min-max normalization reproduces one
    enumerated ``OpponentType`` point for point. Not triangular: a 2-option triangular evaluator is identically
    zero, which would make the sheet degenerate."""
    return ScoreSheet("target", ((0.0, 1 / 3, 2 / 3), (1 / 3, 0.0)), threshold)


def test_on_grid_sheet_maps_to_its_own_type_at_zero_distance():
    belief = BeliefState(OPTION_COUNTS)
    truth = ba.true_opponent(on_grid_sheet(), DEALS, belief)
    assert truth.type_distance == pytest.approx(0.0, abs=1e-9)
    matched = belief.types[truth.type_index]
    assert matched.threshold == pytest.approx(0.55)
    assert np.allclose(matched.weights, (2 / 3, 1 / 3))
    assert matched.shapes == ("uphill", "downhill")
    assert np.allclose(belief.type_utility_matrix(DEALS)[truth.type_index],
                       ba.normalized_utility(on_grid_sheet(), DEALS)[0])


def test_an_off_grid_sheet_maps_to_a_positive_distance_type_that_is_still_the_closest():
    sheet = ScoreSheet("t", ((9.0, 4.0, 0.0), (0.0, 6.0)), 7.0)
    belief = BeliefState(OPTION_COUNTS)
    truth = ba.true_opponent(sheet, DEALS, belief)
    assert truth.type_distance > 0.0
    utility, threshold, _ = ba.normalized_utility(sheet, DEALS)
    U = belief.type_utility_matrix(DEALS)
    dist = np.sqrt(((U - utility[None, :]) ** 2).mean(axis=1)) \
        + np.abs(np.asarray(belief.type_thresholds()) - threshold)
    assert int(np.argmin(dist)) == truth.type_index


def test_accept_set_comes_from_raw_points_not_the_normalization():
    sheet = ScoreSheet("t", ((9.0, 4.0, 0.0), (0.0, 6.0)), 7.0)
    truth = ba.true_opponent(sheet, DEALS, BeliefState(OPTION_COUNTS))
    assert list(truth.accepts) == [sheet.utility(tuple(d)) >= 7.0 for d in DEALS]


def test_degenerate_sheet_normalizes_without_dividing_by_zero():
    flat = ScoreSheet("flat", ((2.0, 2.0, 2.0), (1.0, 1.0)), 5.0)
    truth = ba.true_opponent(flat, DEALS, BeliefState(OPTION_COUNTS))
    assert not truth.accepts.any() and np.isfinite(truth.type_distance)
    assert ba.normalized_utility(flat, DEALS)[1] == 1.0        # an unmeetable threshold sits above the span


def test_a_posterior_collapsed_on_the_true_type_scores_perfectly():
    belief = BeliefState(OPTION_COUNTS, floor=0.0)
    truth = ba.true_opponent(on_grid_sheet(), DEALS, belief)
    belief._post = np.zeros(len(belief.types))
    belief._post[truth.type_index] = 1.0
    scores = ba.metrics(belief, DEALS, truth)
    assert scores == pytest.approx(ba.PERFECT)


def test_the_uniform_prior_is_neither_perfect_nor_degenerate():
    belief = BeliefState(OPTION_COUNTS)
    scores = ba.metrics(belief, DEALS, ba.true_opponent(on_grid_sheet(), DEALS, belief))
    assert 0.0 < scores["posterior_mass_true_type"] < 1.0
    assert scores["expected_utility_rmse"] > 0.0
    assert 0.0 <= scores["accept_set_f1"] <= 1.0


def test_metrics_improve_on_an_informative_concession_sequence():
    """An opponent opening at its ideal and conceding down its own utility ordering is exactly the evidence the
    Chang-Fujita likelihood is built for, so identification and both accuracy scores must end better."""
    belief = BeliefState(OPTION_COUNTS)
    truth = ba.true_opponent(on_grid_sheet(), DEALS, belief)
    before = ba.metrics(belief, DEALS, truth)
    for row in np.argsort(-belief.type_utility_matrix(DEALS)[truth.type_index]):
        belief.observe(tuple(int(x) for x in DEALS[row]))
    after = ba.metrics(belief, DEALS, truth)
    assert after["posterior_mass_true_type"] > before["posterior_mass_true_type"]
    assert after["expected_utility_rmse"] < before["expected_utility_rmse"]
    assert after["accept_set_f1"] >= before["accept_set_f1"]


def test_f1_edge_cases():
    empty = np.zeros(4, dtype=bool)
    assert ba.f1(empty, empty) == 1.0
    assert ba.f1(empty, ~empty) == 0.0
    assert ba.f1(np.array([True, True, False, False]),
                 np.array([True, False, False, False])) == pytest.approx(2 / 3)


def test_auc_is_the_time_mean_not_a_length_dependent_area():
    assert ba.auc([0.5]) == pytest.approx(0.5)
    assert ba.auc([0.0, 1.0]) == pytest.approx(0.5)
    assert ba.auc([1.0] * 9) == pytest.approx(1.0)
    assert ba.auc([]) == 0.0


def test_type_utility_matrix_agrees_between_the_cached_and_on_the_fly_paths():
    """The cached full-space tensor and the subset path must return the same numbers, or a diagnostic computed
    on a deal subset would silently disagree with the same slice of a full one."""
    belief = BeliefState(OPTION_COUNTS)
    full = belief.type_utility_matrix(DEALS)
    subset = DEALS[:3]
    assert np.allclose(belief.type_utility_matrix(subset), full[:, :3])
