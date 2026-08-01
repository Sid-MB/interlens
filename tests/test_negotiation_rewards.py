# [rational_agents: grpo-fairness] 2026-08-01 — property tests for the smoothed log-Nash training reward.
"""The reward's load-bearing properties, as tests: monotonicity, the C1 join at ``eps``, the walk-away ordering,
concavity (which is what does the fairness work), and the lambda-mixture identities."""
from __future__ import annotations

import math

import pytest

from interlens.arena.negotiation.rewards import (DEFAULT_EPS, mixture_rewards, no_deal_utility, potential,
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
