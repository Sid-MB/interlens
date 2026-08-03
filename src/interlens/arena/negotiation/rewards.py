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

Every function takes an optional ``g_floor``, added for fairness-GRPO **v2**. Default ``None`` reproduces the
shape above exactly, so the v1 pilot's numbers stay byte-reproducible. With a floor the per-party utility is
clipped from below at a constant, which bounds the violation branch's dynamic range: v1 measured that the
unbounded tail made the objective behave as an IR-violation penalty rather than as Nash welfare (one party at
``z = -0.2`` is worth ``-25.6``), so nearly all gradient landed on "did anyone get shorted" and none on "was the
surplus divided well". ``violation_decomposition`` is the measurement that turns that diagnosis into a number
and calibrates the floor.

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


def smoothed_log_utility(z: float, *, eps: float = DEFAULT_EPS, g_floor: float | None = None) -> float:
	"""Per-party utility ``g(z)`` of a normalized surplus: ``log z`` for ``z >= eps``, and below that the tangent
	line ``log(eps) + (z - eps) / eps`` (same value and slope at ``eps``, so ``g`` is C1 and strictly increasing
	on the whole real line). Unbounded below by default, which was the original intent: deep threshold violations
	are meant to hurt.

	``g_floor`` clips that unbounded tail from below at a constant, ``max(g(z), g_floor)``. Leave it ``None`` for
	the original unbounded shape. Pass a value when the *dynamic range* of the violation branch is the problem
	rather than its direction: because the linear branch is unbounded, one party at ``z = -0.2`` contributes
	``-25.6`` against a well-behaved deal's ``-2``ish, so nearly all variance in ``table_reward`` — and therefore
	nearly all gradient — lives in "did anybody get shorted" rather than in "was the surplus divided well". A
	floor bounds the violation term's contribution and lets the among-IR region carry the signal, at the cost of
	making ``g`` non-strict (flat) below the crossing point ``z*`` where ``g(z*) = g_floor``.

	**The floor must sit strictly below** :func:`no_deal_utility` (``-5.605`` at the default ``eps``) or the
	ordering inverts and a below-threshold agreement becomes worth more than walking away, which is the one
	ordering the linear branch exists to protect. This is checked, not documented-and-hoped."""
	if eps <= 0:
		raise ValueError(f"eps must be positive, got {eps}")
	z = float(z)
	g = math.log(z) if z >= eps else math.log(eps) + (z - eps) / eps
	if g_floor is None:
		return g
	walk = math.log(eps) - 1.0
	if g_floor >= walk:
		raise ValueError(
			f"g_floor must be strictly below the walk-away value g(0) = {walk:.4f} (got {g_floor}); at or above "
			"it a below-threshold agreement would score no worse than no agreement and the reward would prefer "
			"signing bad deals to walking")
	return max(g, g_floor)


def no_deal_utility(*, eps: float = DEFAULT_EPS, g_floor: float | None = None) -> float:
	"""The utility every seat receives when the episode ends with no deal: ``g(0) = log(eps) - 1``
	(``-5.605`` at the default ``eps``). Sits strictly below any weakly-IR deal (``z >= 0`` scores ``>= g(0)``)
	and strictly above deals that push a party below ``z = 0``. ``g_floor`` is accepted (and validated) for
	signature symmetry with the rest of the module but cannot change this value, since a legal floor is by
	definition below it."""
	return smoothed_log_utility(0.0, eps=eps, g_floor=g_floor)


def table_reward(z: Sequence[float] | None, *, n_agents: int | None = None,
                 eps: float = DEFAULT_EPS, g_floor: float | None = None) -> float:
	"""Table-welfare term ``R_table = mean_i g(z_i)`` on a closed deal, the smoothed log form of normalized Nash
	welfare. ``z=None`` means no deal and returns ``no_deal_utility`` (``n_agents`` is then unused — the mean of a
	constant is that constant). ``g_floor`` clips each party's term from below; see
	:func:`smoothed_log_utility`."""
	if z is None:
		return no_deal_utility(eps=eps, g_floor=g_floor)
	vals = [smoothed_log_utility(v, eps=eps, g_floor=g_floor) for v in z]
	if not vals:
		raise ValueError("empty normalized-surplus vector; pass None for a no-deal episode")
	if n_agents is not None and len(vals) != n_agents:
		raise ValueError(f"expected {n_agents} parties, got {len(vals)}")
	return sum(vals) / len(vals)


def violation_decomposition(z: Sequence[float] | None, *, eps: float = DEFAULT_EPS,
                            g_floor: float | None = None) -> tuple[float, float]:
	"""Split ``table_reward`` into ``(among_ir, violation)`` with ``among_ir + violation == table_reward(z)``.

	``among_ir = mean_i g(max(z_i, eps))`` is what the table would score if every shorted party were pinned at
	its own threshold — the pure *distribution* term, which varies only with how well the surplus is divided
	among parties that cleared their walk-away. ``violation = mean_i [g(z_i) - g(max(z_i, eps))] <= 0`` is the
	penalty for shorting parties, and is exactly zero on an individually rational deal.

	The split exists to be *measured*: taking the variance of each component over a campaign answers "how much of
	the reward's dynamic range is the violation branch", which is the diagnosis of the v1 fairness-GRPO negative
	(the objective was nominally Nash welfare but behaviourally an IR-violation penalty) and the calibration
	target for ``g_floor``. A no-deal episode is not a violation: it returns ``(no_deal_utility, 0.0)``."""
	if z is None:
		return no_deal_utility(eps=eps, g_floor=g_floor), 0.0
	vals = [smoothed_log_utility(v, eps=eps, g_floor=g_floor) for v in z]
	pinned = [smoothed_log_utility(max(float(v), eps), eps=eps, g_floor=g_floor) for v in z]
	if not vals:
		raise ValueError("empty normalized-surplus vector; pass None for a no-deal episode")
	among = sum(pinned) / len(pinned)
	return among, sum(vals) / len(vals) - among


def mixture_rewards(z: Sequence[float] | None, *, lam: float, n_agents: int | None = None,
                    eps: float = DEFAULT_EPS, g_floor: float | None = None) -> list[float]:
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
		return [no_deal_utility(eps=eps, g_floor=g_floor)] * n_agents
	own = [smoothed_log_utility(v, eps=eps, g_floor=g_floor) for v in z]
	if n_agents is not None and len(own) != n_agents:
		raise ValueError(f"expected {n_agents} parties, got {len(own)}")
	shared = sum(own) / len(own)
	return [(1.0 - lam) * g + lam * shared for g in own]


# ------------------------------------------------------------------- shaping --
def potential(z: Sequence[float] | None, *, eps: float = DEFAULT_EPS,
              g_floor: float | None = None) -> float:
	"""Shaping potential ``Phi(s) = max(R_table(standing offer at s), g(0))`` — how good the table is right now.
	With no standing offer this is ``no_deal_utility``, so the first offer is credited by how much better than
	walking it is.

	The floor at ``g(0)`` is what makes this usable as a shaping term. ``table_reward`` is unbounded below (the
	linear branch is deliberately so, to keep gradient on threshold violations), so an absurd proposal could
	otherwise drive ``Phi`` to -100 and produce a shaping increment an order of magnitude larger than the
	episode reward it is supposed to densify. Flooring is not a fudge: a standing offer worse than no agreement
	is worth no more than no agreement, because any party can simply refuse it. ``Phi`` is still a pure function
	of the state, so potential-based shaping's policy-invariance guarantee is untouched, and the increment is now
	bounded by ``|g(0)|``. ``g_floor`` (see :func:`smoothed_log_utility`) additionally bounds each party's term
	before the mean is taken; with a floor in play this ``max`` is rarely the binding constraint, but it is kept
	so ``Phi`` has the same meaning under both reward shapes."""
	return max(table_reward(z, eps=eps, g_floor=g_floor), no_deal_utility(eps=eps, g_floor=g_floor))


def shaping_reward(z_before: Sequence[float] | None, z_after: Sequence[float] | None, *,
                   gamma: float = 1.0, eps: float = DEFAULT_EPS, g_floor: float | None = None) -> float:
	"""Potential-based shaping increment ``gamma * Phi(s') - Phi(s)`` for one turn: "did your move pull the
	standing offer toward or away from a fair deal?". Potential-based shaping provably preserves the optimal
	policy (Ng, Harada & Russell 1999), so this densifies credit assignment over a ~25-round episode without
	changing what is being optimized. ``gamma`` should match the discount used by the learner (``1.0`` for the
	undiscounted episodic setting)."""
	return (gamma * potential(z_after, eps=eps, g_floor=g_floor)
	        - potential(z_before, eps=eps, g_floor=g_floor))
