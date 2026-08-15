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

"""Bundle values, the EXACTNESS of the efficient-allocation solver (verified against brute force, including
synergies and capacities), and the payment rules on textbook examples.

Exactness is not asserted here, it is checked: every efficiency and suppression number in the campaign
divides by ``max_welfare``, so the solver is compared against exhaustive enumeration on generated instances
as well as on hand cases."""
from __future__ import annotations

import numpy as np
import pytest

from interlens.arena.auction.allocation import (Allocation, ValueModel, brute_force_allocation,
                                                clinching_prices, max_weight_assignment,
                                                sealed_single_outcome, uniform_price_clear, vcg_payments)
from interlens.arena.auction.spec import Mechanism, generate_spec


def _vm(values, *, capacities=None, decays=None, rates=None, targets=None, budgets=None) -> ValueModel:
    values = np.array(values, dtype=np.int64)
    n = values.shape[0]
    return ValueModel(values=values,
                      capacities=tuple(capacities or [values.shape[1]] * n),
                      decays=tuple(decays or [1.0] * n),
                      synergy_rates=tuple(rates or [0.0] * n),
                      synergy_targets=tuple(targets or [None] * n),
                      budgets=tuple(budgets) if budgets else None)


# ----------------------------------------------------------------- bundle values ---
def test_bundle_value_applies_decay_capacity_and_synergy_by_hand():
    vm = _vm([[10, 6, 4]], capacities=[2], decays=[0.5], rates=[0.25], targets=[(0, 1)])
    assert vm.bundle_value(0, ()) == 0.0
    assert vm.bundle_value(0, (2,)) == 4.0
    # {0,1}: 10 * 0.5^0 + 6 * 0.5^1 = 13, plus synergy 0.25 * (10 + 6) = 4 -> 17
    assert vm.bundle_value(0, (0, 1)) == pytest.approx(17.0)
    # {1,2} does not contain the target set, so no bonus: 6 + 4 * 0.5 = 8
    assert vm.bundle_value(0, (1, 2)) == pytest.approx(8.0)
    assert vm.bundle_value(0, (0, 1, 2)) == float("-inf")       # capacity 2


def test_assignment_solver_matches_hand_computed_optimum():
    value = np.array([[7.0, 2.0], [4.0, 5.0]])
    cols, total = max_weight_assignment(value)
    assert total == pytest.approx(12.0) and cols.tolist() == [0, 1]


# ------------------------------------------------------------------- exactness ---
def test_efficient_allocation_matches_brute_force_on_hand_case_with_synergy():
    # Seat 0 values {0,1} highly only together; seat 1 outbids it item by item.
    vm = _vm([[6, 6, 1], [7, 7, 1]], capacities=[2, 2], rates=[1.0, 0.0], targets=[(0, 1), None])
    alloc, w = vm.efficient_allocation()
    b_alloc, b_w = brute_force_allocation(vm)
    assert w == pytest.approx(b_w)
    assert alloc.bundle(0) == (0, 1)                    # 12 + 12 synergy = 24 beats 14 for seat 1
    assert w == pytest.approx(24.0 + 1.0)               # seat 1 still takes lot 2


@pytest.mark.parametrize("n_items", [2, 3, 4])
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4, 5])
def test_efficient_allocation_is_exact_on_generated_instances(n_items, seed):
    spec = generate_spec(seed, mechanism=Mechanism.saa(n_items), value_structure="apv", horizon=2)
    for t in (1, 2):
        vm = ValueModel.from_spec(spec, t)
        _, w = vm.efficient_allocation()
        _, brute = brute_force_allocation(vm)
        assert w == pytest.approx(brute, rel=1e-9)


def test_efficient_allocation_respects_capacity():
    vm = _vm([[10, 10, 10], [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1]], capacities=[1, 1, 1, 1, 1])
    alloc, w = vm.efficient_allocation()
    assert len(alloc.bundle(0)) == 1 and w == pytest.approx(12.0)


def test_unsold_is_always_available_so_welfare_is_never_negative():
    vm = _vm([[1]], capacities=[1])
    alloc, w = vm.efficient_allocation()
    assert w >= 0.0 and Allocation.empty(1).winners() == ()


# -------------------------------------------------------------------- payments ---
def test_vcg_is_the_second_price_on_a_single_lot():
    vm = _vm([[10], [7], [3]], capacities=[1, 1, 1])
    pay, alloc = vcg_payments(vm)
    assert alloc.winner_of == (0,)
    assert pay[0] == pytest.approx(7.0) and pay[1] == 0.0 and pay[2] == 0.0


def test_vcg_charges_the_externality_on_two_lots():
    # Seat 0 wins both; without it the others would have taken them for 5 + 4.
    vm = _vm([[10, 8], [5, 1], [1, 4]], capacities=[2, 1, 1])
    pay, alloc = vcg_payments(vm)
    assert alloc.bundle(0) == (0, 1)
    assert pay[0] == pytest.approx(9.0)


def test_sealed_single_outcome_prices_and_breaks_ties_by_the_seeded_permutation():
    assert sealed_single_outcome([10, 7, 3], pricing="second_price", tie_break=(0, 1, 2)) == (0, 7)
    assert sealed_single_outcome([10, 7, 3], pricing="first_price", tie_break=(0, 1, 2)) == (0, 10)
    # A tie goes to whoever comes first in the announced permutation, not to the lower seat index.
    assert sealed_single_outcome([9, 9, 3], pricing="second_price", tie_break=(1, 0, 2)) == (1, 9)
    assert sealed_single_outcome([None, None, None], pricing="second_price", tie_break=(0, 1, 2)) == (None, 0)
    assert sealed_single_outcome([4, 3], pricing="second_price", tie_break=(0, 1), reserve=6) == (None, 0)


def test_uniform_price_clears_at_the_highest_rejected_bid():
    # Three units; unit bids 10, 8 (seat 0) and 9, 5 (seat 1). Top three: 10, 9, 8; highest rejected = 5.
    units, price = uniform_price_clear([[10, 8], [9, 5]], supply=3, tie_break=(0, 1))
    assert units.tolist() == [2, 1] and price == 5
    # With nothing rejected the price falls to the reserve.
    units, price = uniform_price_clear([[10], [9]], supply=3, tie_break=(0, 1), reserve=2)
    assert units.tolist() == [1, 1] and price == 2


def test_clinching_reproduces_the_vickrey_payment_on_a_hand_case():
    # Two units, three bidders with marginal values (10, 9), (8,), (4,). Bidder 0 values both units above
    # every rival, so it wins both: it clinches the first as bidder 2 leaves at 4, the second as bidder 1
    # leaves at 8. Total 12 -- exactly the VCG payment, which is the point of the clinching rule.
    units, pay = clinching_prices([[10, 9], [8], [4]], supply=2, increment=1)
    assert units.tolist() == [2, 0, 0]
    assert pay[0] == pytest.approx(12.0) and pay[1] == 0.0
    # The same allocation priced by the pivot rule on two distinct lots agrees: 8 + 4 of foregone welfare.
    vcg, _ = vcg_payments(_vm([[10, 9], [8, 8], [4, 4]], capacities=[2, 1, 1]))
    assert vcg[0] == pytest.approx(12.0)


def test_clinching_awards_everything_when_demand_never_exceeds_supply():
    units, pay = clinching_prices([[10], [9]], supply=3, increment=1, reserve=0)
    assert units.tolist() == [1, 1] and pay.tolist() == [0.0, 0.0]


def test_allocation_json_round_trip():
    a = Allocation((0, None, 3))
    assert Allocation.from_json(a.to_json()) == a
