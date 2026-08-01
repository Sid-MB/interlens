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

# [rational_agents: grpo-fairness] 2026-08-01 — training-reward layer for the fairness-GRPO pilot
# (proposal experiments/rational_agents/proposals/2026-08-01-fairness-grpo.md).
"""Outcome rewards for RL on scorable negotiation: the smoothed log-Nash objective.

Everything here is a pure function of the **normalized surplus vector** ``z = (z_i)``, ``z_i = (u_i(d) - tau_i)
/ c_i``, where ``c_i`` is party ``i``'s unconstrained maximum surplus. That is exactly the
``outcome.normalized_realized_surplus`` an episode already records, so a reward computed here is **text-blind**:
it never reads a token the policy generated, only the engine's scoring of the deal it closed.

Why this shape (see the proposal for the full argument):

* ``smoothed_log_utility`` is ``log z`` above ``eps`` — so ``table_reward`` is a monotone transform of normalized
  Nash welfare wherever every party clears threshold, and training optimizes the judgment metric rather than a
  proxy. Concavity does the fairness work: moving surplus from a rich party to a poor one always raises the mean.
* Below ``eps`` it continues **linearly** with the slope ``log`` has at ``eps``. Plain ``log``/NNW is flat (zero)
  everywhere a party is below threshold, which is precisely where the observed pathology lives, so RL would get
  no gradient there. The linear branch restores slope while preserving the ordering — a below-threshold outcome
  still scores worse than every individually rational one.
* Walking away pays ``no_deal_utility`` (``= g(0)``) to every seat: worse than any weakly-IR deal, better than a
  deeply below-threshold one. Walking is priced, not free and not catastrophic.
* ``z`` is affine-invariant in each party's private score sheet, so no arm can win by rescaling its own points.

``mixture_rewards`` implements the per-seat objective ``R_i(lam) = (1 - lam) * g(z_i) + lam * R_table``, the
self-interest/table-welfare mixture whose sweep is the experiment. ``potential`` is the potential-based shaping
term ``Phi(s) = R_table(standing offer at s)``; ``shaping_reward`` forms ``gamma * Phi(s') - Phi(s)``, which by
Ng-Harada-Russell leaves the optimal policy unchanged while densifying credit over a long episode.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

DEFAULT_EPS = 0.01
"""Threshold below which ``smoothed_log_utility`` switches from ``log`` to its linear continuation."""


def smoothed_log_utility(z: float, *, eps: float = DEFAULT_EPS) -> float:
	"""Per-party utility ``g(z)`` of a normalized surplus: ``log z`` for ``z >= eps``, and below that the tangent
	line ``log(eps) + (z - eps) / eps`` (same value and slope at ``eps``, so ``g`` is C1 and strictly increasing
	on the whole real line). Unbounded below, which is intended: deep threshold violations are meant to hurt."""
	if eps <= 0:
		raise ValueError(f"eps must be positive, got {eps}")
	z = float(z)
	if z >= eps:
		return math.log(z)
	return math.log(eps) + (z - eps) / eps


def no_deal_utility(*, eps: float = DEFAULT_EPS) -> float:
	"""The utility every seat receives when the episode ends with no deal: ``g(0) = log(eps) - 1``
	(``-5.605`` at the default ``eps``). Sits strictly below any weakly-IR deal (``z >= 0`` scores ``>= g(0)``)
	and strictly above deals that push a party below ``z = 0``."""
	return smoothed_log_utility(0.0, eps=eps)


def table_reward(z: Sequence[float] | None, *, n_agents: int | None = None,
                 eps: float = DEFAULT_EPS) -> float:
	"""Table-welfare term ``R_table = mean_i g(z_i)`` on a closed deal, the smoothed log form of normalized Nash
	welfare. ``z=None`` means no deal and returns ``no_deal_utility`` (``n_agents`` is then unused — the mean of a
	constant is that constant)."""
	if z is None:
		return no_deal_utility(eps=eps)
	vals = [smoothed_log_utility(v, eps=eps) for v in z]
	if not vals:
		raise ValueError("empty normalized-surplus vector; pass None for a no-deal episode")
	if n_agents is not None and len(vals) != n_agents:
		raise ValueError(f"expected {n_agents} parties, got {len(vals)}")
	return sum(vals) / len(vals)


def mixture_rewards(z: Sequence[float] | None, *, lam: float, n_agents: int | None = None,
                    eps: float = DEFAULT_EPS) -> list[float]:
	"""Per-seat episode rewards ``R_i(lam) = (1 - lam) * g(z_i) + lam * R_table``, one per party in seat order.

	``lam=0`` is pure self-interest (the manipulation check: it should reproduce the observed pathologies),
	``lam=1`` is pure table welfare (identical for every seat), and intermediate values trace the frontier
	between them. On a no-deal episode (``z=None``) every seat gets ``no_deal_utility`` at any ``lam``, so
	``n_agents`` is required to size the output."""
	if not 0.0 <= lam <= 1.0:
		raise ValueError(f"lam must be in [0, 1], got {lam}")
	if z is None:
		if n_agents is None:
			raise ValueError("n_agents is required to size the reward vector on a no-deal episode")
		return [no_deal_utility(eps=eps)] * n_agents
	own = [smoothed_log_utility(v, eps=eps) for v in z]
	if n_agents is not None and len(own) != n_agents:
		raise ValueError(f"expected {n_agents} parties, got {len(own)}")
	shared = sum(own) / len(own)
	return [(1.0 - lam) * g + lam * shared for g in own]


# ------------------------------------------------------------------- shaping --
def potential(z: Sequence[float] | None, *, eps: float = DEFAULT_EPS) -> float:
	"""Shaping potential ``Phi(s) = max(R_table(standing offer at s), g(0))`` — how good the table is right now.
	With no standing offer this is ``no_deal_utility``, so the first offer is credited by how much better than
	walking it is.

	The floor at ``g(0)`` is what makes this usable as a shaping term. ``table_reward`` is unbounded below (the
	linear branch is deliberately so, to keep gradient on threshold violations), so an absurd proposal could
	otherwise drive ``Phi`` to -100 and produce a shaping increment an order of magnitude larger than the
	episode reward it is supposed to densify. Flooring is not a fudge: a standing offer worse than no agreement
	is worth no more than no agreement, because any party can simply refuse it. ``Phi`` is still a pure function
	of the state, so potential-based shaping's policy-invariance guarantee is untouched, and the increment is now
	bounded by ``|g(0)|``."""
	return max(table_reward(z, eps=eps), no_deal_utility(eps=eps))


def shaping_reward(z_before: Sequence[float] | None, z_after: Sequence[float] | None, *,
                   gamma: float = 1.0, eps: float = DEFAULT_EPS) -> float:
	"""Potential-based shaping increment ``gamma * Phi(s') - Phi(s)`` for one turn: "did your move pull the
	standing offer toward or away from a fair deal?". Potential-based shaping provably preserves the optimal
	policy (Ng, Harada & Russell 1999), so this densifies credit assignment over a ~25-round episode without
	changing what is being optimized. ``gamma`` should match the discount used by the learner (``1.0`` for the
	undiscounted episodic setting)."""
	return gamma * potential(z_after, eps=eps) - potential(z_before, eps=eps)
