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

# [rational_agents restructure: phase-C] 2026-07-24 — moved up from experiments/rational_agents/analysis/:
# negotiation-generic measurement, reusable by any experiment over this game family.
"""Trajectory-shape metrics over a *series* (not a single turn). Pure numpy (no scipy).

- **Concession-curve fit** ``y(x) = d + b*tanh(a*x - c)``, burstiness ``tau = |a|*|b|`` and Concession-Rigidity
  Index ``CRI = 1 - 1.32/(|a|*T)`` (LLM Rationalis arXiv:2512.13063 §3) — smooth vs rigid all-or-nothing
  concession. Fit by multi-start damped Gauss–Newton (the tanh fit is non-convex).
- **No-regret trend tests** (Park et al. arXiv:2403.16843 §3.1) over a per-turn regret series: a Mann–Kendall
  trend test for a decreasing average regret ``Regret_t/t``, and a log–log slope of cumulative regret
  (``b0 < 1`` ⇒ sublinear ⇒ no-regret).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np


# ============================================================== concession curve ==
@dataclass
class ConcessionFit:
	"""Fitted ``y(x) = d + b*tanh(a*x - c)`` on normalized turn-fraction x∈[0,1] and normalized concession
	y∈[0,1], plus the derived shape metrics. ``n`` is the number of offers fitted; ``rmse`` the fit residual
	(a large rmse means the tanh family does not describe this trajectory — read τ/CRI with care)."""

	a: float
	b: float
	c: float
	d: float
	tau: float          # burstiness |a|*|b| — how sharply concession is concentrated in time
	cri: float          # Concession-Rigidity Index 1 - 1.32/(|a|*T), clamped to [0,1]
	rmse: float
	n: int

	def to_json(self) -> dict:
		return asdict(self)


def _tanh_model(p, x):
	a, b, c, d = p
	return d + b * np.tanh(a * x - c)


def _tanh_jac(p, x):
	a, b, c, _d = p
	z = a * x - c
	sech2 = 1.0 - np.tanh(z) ** 2
	return np.stack([b * sech2 * x, np.tanh(z), -b * sech2, np.ones_like(x)], axis=1)


def _gauss_newton(x, y, p0, iters: int = 100):
	"""One Levenberg–Marquardt run from init ``p0``; returns (params, sse)."""
	p = np.array(p0, dtype=float)
	lam = 1e-2
	r = y - _tanh_model(p, x)
	sse = float(r @ r)
	for _ in range(iters):
		J = _tanh_jac(p, x)
		JTJ = J.T @ J
		g = J.T @ r
		step = np.linalg.solve(JTJ + lam * np.eye(4), g)
		p_new = p + step
		r_new = y - _tanh_model(p_new, x)
		sse_new = float(r_new @ r_new)
		if sse_new < sse:
			p, r, sse, lam = p_new, r_new, sse_new, max(lam * 0.5, 1e-9)
		else:
			lam = min(lam * 3.0, 1e6)
			if lam >= 1e6:
				break
	return p, sse


def fit_concession_curve(values, *, normalize: bool = True) -> ConcessionFit:
	"""Fit the tanh concession model to a sequence of a party's successive offer *values* (in the order made).

	``values`` is the party's own-surplus (or its own offered price) at each of its offers; the x-axis is the
	turn fraction of that offer (evenly spaced in [0,1]). With ``normalize=True`` (the LLM Rationalis
	convention) y is min-max scaled to [0,1] so ``a``/``b``/``tau`` are comparable across parties and games; the
	burstiness ``tau`` and CRI are always computed on the normalized fit. Needs >= 3 offers (returns a fit with
	``n < 3`` and ``nan`` shape metrics otherwise, since a step cannot be identified from two points)."""
	y_raw = np.asarray(values, dtype=float)
	n = int(y_raw.size)
	if n < 3:
		return ConcessionFit(*(float("nan"),) * 7, n=n)
	x = np.linspace(0.0, 1.0, n)
	if normalize:
		span = float(y_raw.max() - y_raw.min())
		y = (y_raw - y_raw.min()) / span if span > 0 else np.zeros_like(y_raw)
	else:
		y = y_raw
	# multi-start over slope sign/magnitude and midpoint — tanh fitting is non-convex
	d0 = float(np.median(y))
	b0 = float((y[-1] - y[0]) / 2.0) or 0.5
	best_p, best_sse = None, math.inf
	for a0 in (-10.0, -5.0, -1.0, 1.0, 5.0, 10.0):
		for c0 in (0.0, a0 * 0.5, a0):
			p, sse = _gauss_newton(x, y, [a0, b0, c0, d0])
			if sse < best_sse:
				best_p, best_sse = p, sse
	a, b, c, d = (float(v) for v in best_p)
	rmse = math.sqrt(best_sse / n)
	tau = abs(a) * abs(b)
	cri_raw = 1.0 - 1.32 / (abs(a) * n) if a != 0 else float("nan")
	cri = min(max(cri_raw, 0.0), 1.0) if not math.isnan(cri_raw) else cri_raw
	return ConcessionFit(a=a, b=b, c=c, d=d, tau=tau, cri=cri, rmse=rmse, n=n)


# ================================================================ no-regret tests ==
def _normal_cdf(z: float) -> float:
	return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


@dataclass
class NoRegretTrend:
	"""Mann–Kendall test for a *decreasing* trend in average regret ``Regret_t / t`` (Park §3.1 / Prop. 1).

	``trend_pvalue`` is the one-sided p-value for the decreasing alternative: small p ⇒ average regret is
	significantly decreasing ⇒ evidence of no-regret behavior (``no_regret_evidence`` at α=0.05). ``mk_s`` is the
	Mann–Kendall statistic (negative = downward), ``mean_avg_regret`` the mean of ``Regret_t/t``."""

	n: int
	mk_s: int
	z: float
	trend_pvalue: float
	no_regret_evidence: bool
	mean_avg_regret: float

	def to_json(self) -> dict:
		return asdict(self)


def no_regret_trend_test(per_turn_regret, *, alpha: float = 0.05) -> NoRegretTrend:
	"""Park trend test on a per-turn regret series (r_t >= 0, surplus-loss units).

	Forms cumulative regret ``R_t = sum_{s<=t} r_s`` then average regret ``a_t = R_t/t`` and runs Mann–Kendall
	for a monotone decreasing trend in ``a_t``. Needs >= 3 turns. Ties are corrected in the variance; a
	continuity correction is applied to S."""
	r = np.asarray(per_turn_regret, dtype=float)
	n = int(r.size)
	if n < 3:
		return NoRegretTrend(n=n, mk_s=0, z=float("nan"), trend_pvalue=float("nan"),
		                     no_regret_evidence=False, mean_avg_regret=float(r.mean()) if n else float("nan"))
	cum = np.cumsum(r)
	a_t = cum / np.arange(1, n + 1)
	s = 0
	for i in range(n - 1):
		s += int(np.sum(np.sign(a_t[i + 1:] - a_t[i])))
	# variance with tie correction
	_, counts = np.unique(a_t, return_counts=True)
	tie = float(np.sum(counts * (counts - 1) * (2 * counts + 5)))
	var = (n * (n - 1) * (2 * n + 5) - tie) / 18.0
	if var <= 0:
		z = 0.0
	elif s > 0:
		z = (s - 1) / math.sqrt(var)
	elif s < 0:
		z = (s + 1) / math.sqrt(var)
	else:
		z = 0.0
	p_decreasing = _normal_cdf(z)  # left tail: strongly negative z ⇒ small p ⇒ decreasing
	return NoRegretTrend(n=n, mk_s=int(s), z=float(z), trend_pvalue=float(p_decreasing),
	                     no_regret_evidence=bool(p_decreasing < alpha), mean_avg_regret=float(a_t.mean()))


@dataclass
class LogLogRegret:
	"""Log–log regression ``log R_t = b0 log t + b1`` of cumulative regret (Park §3.1). ``b0 < 1`` ⇒ sublinear
	cumulative regret ⇒ no-regret. ``r2`` is the fit quality; ``n_points`` the turns with positive cumulative
	regret (log is undefined at zero, so leading zero-regret turns are dropped)."""

	beta0: float
	intercept: float
	r2: float
	sublinear: bool
	n_points: int

	def to_json(self) -> dict:
		return asdict(self)


def loglog_regret_slope(per_turn_regret) -> LogLogRegret:
	"""Fit the log–log slope of cumulative regret. Returns ``nan`` slope if fewer than 2 turns have positive
	cumulative regret (a flat zero-regret series is trivially sublinear but the slope is unidentified)."""
	r = np.asarray(per_turn_regret, dtype=float)
	cum = np.cumsum(r)
	t = np.arange(1, r.size + 1)
	mask = cum > 0
	if int(mask.sum()) < 2:
		return LogLogRegret(beta0=float("nan"), intercept=float("nan"), r2=float("nan"),
		                    sublinear=True, n_points=int(mask.sum()))
	lt, lr = np.log(t[mask]), np.log(cum[mask])
	A = np.vstack([lt, np.ones_like(lt)]).T
	(b0, b1), *_ = np.linalg.lstsq(A, lr, rcond=None)
	pred = A @ np.array([b0, b1])
	ss_res = float(np.sum((lr - pred) ** 2))
	ss_tot = float(np.sum((lr - lr.mean()) ** 2))
	r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
	return LogLogRegret(beta0=float(b0), intercept=float(b1), r2=float(r2),
	                    sublinear=bool(b0 < 1.0), n_points=int(mask.sum()))
