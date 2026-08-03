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

# [rational_agents: grpo-fairness] 2026-08-01 — property tests for the smoothed log-Nash training reward.
"""The reward's load-bearing properties, as tests: monotonicity, the C1 join at ``eps``, the walk-away ordering,
concavity (which is what does the fairness work), and the lambda-mixture identities."""
from __future__ import annotations

import math

import pytest

from interlens.arena.negotiation.rewards import (DEFAULT_EPS, mixture_rewards, no_deal_utility, potential,
                                                 violation_decomposition,
                                                 shaping_reward, smoothed_log_utility, table_reward)


def test_matches_log_above_eps():
	for z in (0.01, 0.1, 0.5, 1.0, 3.0):
		assert smoothed_log_utility(z) == pytest.approx(math.log(z))


def test_c1_join_at_eps():
	"""Value and slope agree at the join, so there is no kink for an optimizer to sit in."""
	eps = DEFAULT_EPS
	h = 1e-7
	left = (smoothed_log_utility(eps) - smoothed_log_utility(eps - h)) / h
	right = (smoothed_log_utility(eps + h) - smoothed_log_utility(eps)) / h
	assert left == pytest.approx(right, rel=1e-3)
	assert left == pytest.approx(1.0 / eps, rel=1e-3)


def test_strictly_increasing_including_below_threshold():
	"""The whole point of the linear branch: gradient survives where plain NNW is flat at zero."""
	zs = [-1.0, -0.5, -0.1, 0.0, 0.005, DEFAULT_EPS, 0.2, 1.0]
	vals = [smoothed_log_utility(z) for z in zs]
	assert all(b > a for a, b in zip(vals, vals[1:]))


def test_walk_value_sits_between_ir_deals_and_threshold_violations():
	"""The ordering the proposal states, which is a claim about ONE party's utility: walking beats being pushed
	below threshold and loses to any deal that clears it. It is deliberately not a claim about the table mean —
	a table where five parties do well and one is moderately short still out-scores everyone walking away, which
	is the welfare accounting we want."""
	walk = no_deal_utility()
	assert walk == pytest.approx(math.log(DEFAULT_EPS) - 1.0)
	assert smoothed_log_utility(-0.2) < walk < smoothed_log_utility(0.05)
	assert table_reward([0.05] * 6) > walk                  # a thin but universally IR deal beats walking
	assert table_reward([-0.2] * 6) < walk                  # a table that shorts everyone is worse than walking


def test_concavity_rewards_equalizing_transfers():
	"""A mean-preserving transfer from a rich party to a poor one must raise the table reward — the fairness
	mechanism, with no bolted-on equality penalty."""
	unequal = [0.9, 0.9, 0.9, 0.9, 0.9, 0.1]
	equal = [0.8, 0.8, 0.8, 0.8, 0.8, 0.6]
	assert sum(unequal) == pytest.approx(sum(equal))
	assert table_reward(equal) > table_reward(unequal)


def test_table_reward_is_log_of_normalized_nash_welfare():
	"""Above eps the objective is a monotone transform of the judgment metric, not a proxy for it."""
	z = [0.3, 0.5, 0.2, 0.9, 0.4, 0.6]
	nnw = math.exp(sum(math.log(v) for v in z) / len(z))
	assert table_reward(z) == pytest.approx(math.log(nnw))


def test_mixture_endpoints_and_seat_average():
	z = [0.2, 0.4, 0.6, 0.8, 0.5, 0.3]
	selfish = mixture_rewards(z, lam=0.0)
	shared = mixture_rewards(z, lam=1.0)
	assert selfish == pytest.approx([smoothed_log_utility(v) for v in z])
	assert shared == pytest.approx([table_reward(z)] * len(z))
	# Averaged over seats the mixture collapses to R_table for every lambda — which is why the campaign-level
	# soundness check is lambda-free and the sweep only changes WHO is paid what.
	for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
		r = mixture_rewards(z, lam=lam)
		assert sum(r) / len(r) == pytest.approx(table_reward(z))


def test_no_deal_pays_every_seat_the_walk_value_at_any_lambda():
	for lam in (0.0, 0.5, 1.0):
		assert mixture_rewards(None, lam=lam, n_agents=6) == pytest.approx([no_deal_utility()] * 6)


def test_shaping_telescopes_to_potential_difference():
	"""Undiscounted shaping over a path sums to Phi(end) - Phi(start), the identity the trainer relies on when
	it credits a turn with (Phi_end - Phi_before)."""
	path = [None, [0.1] * 6, [0.3] * 6, [0.5] * 6]
	total = sum(shaping_reward(a, b) for a, b in zip(path, path[1:]))
	assert total == pytest.approx(potential(path[-1]) - potential(path[0]))


def test_rejects_bad_lambda_and_eps():
	with pytest.raises(ValueError):
		mixture_rewards([0.5] * 6, lam=1.5)
	with pytest.raises(ValueError):
		smoothed_log_utility(0.5, eps=0.0)
	with pytest.raises(ValueError):
		mixture_rewards(None, lam=0.5)      # no-deal without n_agents cannot be sized


# ---------------------------------------------------------------- g_floor (fairness-GRPO v2) --
# [rational_agents: grpo-v2 lane] 2026-08-03 — the clipped violation branch. v1's diagnosis (note 0023) was that
# the unbounded linear tail made the objective an IR-violation penalty wearing a Nash-welfare costume; g_floor is
# the surgery, and these pin the two things that must survive it (the walk-away ordering) and the one thing that
# must not change (v1's numbers at the default).

FLOOR = -8.0


def test_default_is_byte_identical_to_v1():
	"""No g_floor means the v1 shape exactly — note 0023's reward numbers must stay reproducible."""
	for z in (-5.0, -0.2, 0.0, 0.005, DEFAULT_EPS, 0.3, 1.0, 4.0):
		assert smoothed_log_utility(z, g_floor=None) == smoothed_log_utility(z)
	assert table_reward([0.1, -0.3, 0.5], g_floor=None) == table_reward([0.1, -0.3, 0.5])
	assert no_deal_utility(g_floor=None) == no_deal_utility()


def test_floor_clips_the_tail_and_leaves_the_ir_region_untouched():
	assert smoothed_log_utility(-5.0, g_floor=FLOOR) == FLOOR
	assert smoothed_log_utility(-0.2, g_floor=FLOOR) == FLOOR      # v1 valued this at -25.6
	for z in (DEFAULT_EPS, 0.05, 0.3, 1.0):                        # above threshold: unchanged
		assert smoothed_log_utility(z, g_floor=FLOOR) == smoothed_log_utility(z)


def test_walk_away_still_beats_a_below_threshold_deal_PER_PARTY():
	"""The per-party ordering the linear branch exists to protect, and the one a legal floor keeps: from the
	point of view of the party being shorted, being shorted is worse than no agreement at all."""
	walk = no_deal_utility(g_floor=FLOOR)
	for z in (-0.02, -0.5, -5.0):
		assert smoothed_log_utility(z, g_floor=FLOOR) < walk
	assert walk == no_deal_utility()                               # a legal floor cannot move the walk value


def test_clipping_KNOWINGLY_relaxes_the_table_level_walk_ordering():
	"""**The named cost of the surgery, pinned so it cannot be forgotten.**

	Under the v1 unbounded branch a single shorted party dragged the whole table below the walk-away value, so
	the objective could never prefer "short one, serve five" to no deal. A constant floor caps that party's
	contribution at ``g_floor / n``, so a sufficiently well-served majority now outweighs it — which is the same
	property that moves reward variance out of the IR region and into the distribution term. The two cannot be
	separated: any floor tight enough to fix v1's dynamic range is loose enough to permit this.

	v2 therefore does NOT rely on the reward to deter below-threshold agreements. That deterrent moves to a
	preregistered evaluation guard on the below-threshold rate. This test exists to make the trade explicit."""
	assert table_reward([0.5, 0.5, -0.5]) < table_reward(None)                    # v1: majority cannot outweigh
	assert table_reward([0.5, 0.5, -0.5], g_floor=FLOOR) > table_reward(None, g_floor=FLOOR)   # v2: it can


def test_violation_tolerance_is_monotone_in_the_floor():
	"""How many parties at ``z`` it takes to outweigh one clipped party, the scalar version of the trade above:
	a deeper floor buys back more deterrence and less distributional gradient."""

	def tolerance(floor: float, *, z: float = 0.5, n: int = 6) -> bool:
		"""Does a table of ``n`` parties, one shorted and the rest at ``z``, still score below walking?"""
		return table_reward([z] * (n - 1) + [-0.5], g_floor=floor) < no_deal_utility(g_floor=floor)

	assert tolerance(-60.0)          # a floor deep enough to keep v1's deterrent...
	assert not tolerance(-8.0)       # ...and one tight enough to be useful does not


def test_floor_at_or_above_the_walk_value_is_refused():
	for bad in (no_deal_utility(), -5.0, 0.0, 1.0):
		with pytest.raises(ValueError, match="strictly below"):
			smoothed_log_utility(-1.0, g_floor=bad)


def test_floor_preserves_monotonicity_weakly_and_concavity_above_the_crossing():
	zs = [-4.0, -1.0, -0.3, -0.02, 0.0, 0.005, 0.02, 0.2, 1.0]
	vals = [smoothed_log_utility(z, g_floor=FLOOR) for z in zs]
	assert all(b >= a for a, b in zip(vals, vals[1:]))             # non-decreasing (flat below the crossing)
	# Concavity — the property that does the fairness work — still holds among IR outcomes.
	rich, poor = [0.8, 0.05], [0.6, 0.25]
	assert table_reward(poor, g_floor=FLOOR) > table_reward(rich, g_floor=FLOOR)


def test_violation_decomposition_sums_to_the_table_reward():
	for z, floor in [([0.4, 0.2, 0.1], None), ([0.4, -0.2, 0.1], None),
	                 ([0.4, -0.2, 0.1], FLOOR), ([0.4, 0.2, 0.1], FLOOR)]:
		among, viol = violation_decomposition(z, g_floor=floor)
		assert among + viol == pytest.approx(table_reward(z, g_floor=floor))


def test_violation_term_is_zero_exactly_on_ir_deals_and_on_no_deal():
	assert violation_decomposition([0.4, 0.2, 0.1])[1] == 0.0
	among, viol = violation_decomposition(None)
	assert (among, viol) == (no_deal_utility(), 0.0)               # walking is not a violation
	assert violation_decomposition([0.4, -0.01, 0.1])[1] < 0.0


def test_the_floor_shrinks_the_violation_term_and_not_the_distribution_term():
	"""The whole point, as an inequality: clipping compresses the violation branch's range while leaving the
	among-IR term identical, which is what shifts reward variance from 'was anyone shorted' to 'how was it
	divided'."""
	z = [0.5, 0.3, -0.4]
	among_v1, viol_v1 = violation_decomposition(z)
	among_v2, viol_v2 = violation_decomposition(z, g_floor=FLOOR)
	assert among_v2 == among_v1
	assert abs(viol_v2) < abs(viol_v1)


def test_mixture_and_shaping_thread_the_floor():
	z = [0.5, 0.3, -0.4]
	assert mixture_rewards(z, lam=1.0, g_floor=FLOOR) == pytest.approx(
		[table_reward(z, g_floor=FLOOR)] * 3)
	assert mixture_rewards(z, lam=0.0, g_floor=FLOOR) == pytest.approx(
		[smoothed_log_utility(v, g_floor=FLOOR) for v in z])
	# potential is floored twice over (by g_floor per party, then by the walk value); shaping telescopes either way
	assert shaping_reward(None, z, g_floor=FLOOR) == pytest.approx(
		potential(z, g_floor=FLOOR) - potential(None, g_floor=FLOOR))
