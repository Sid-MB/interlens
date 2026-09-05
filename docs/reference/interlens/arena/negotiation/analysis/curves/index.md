# `interlens.arena.negotiation.analysis.curves`

Trajectory-shape metrics over a *series* (not a single turn). Pure numpy (no scipy).

- **Concession-curve fit** `y(x) = d + b*tanh(a*x - c)`, burstiness `tau = |a|*|b|` and Concession-Rigidity
  Index `CRI = 1 - 1.32/(|a|*T)` (LLM Rationalis arXiv:2512.13063 §3) — smooth vs rigid all-or-nothing
  concession. Fit by multi-start damped Gauss–Newton (the tanh fit is non-convex).
- **No-regret trend tests** (Park et al. arXiv:2403.16843 §3.1) over a per-turn regret series: a Mann–Kendall
  trend test for a decreasing average regret `Regret_t/t`, and a log–log slope of cumulative regret
  (`b0 < 1` ⇒ sublinear ⇒ no-regret).

## Classes

| Name | Summary |
|---|---|
| [`ConcessionFit`](ConcessionFit.md) | Fitted `y(x) = d + b*tanh(a*x - c)` on normalized turn-fraction x∈[0,1] and normalized concession y∈[0,1], plus the derived shape metrics. |
| [`LogLogRegret`](LogLogRegret.md) | Log–log regression `log R_t = b0 log t + b1` of cumulative regret (Park §3.1). |
| [`NoRegretTrend`](NoRegretTrend.md) | Mann–Kendall test for a *decreasing* trend in average regret `Regret_t / t` (Park §3.1 / Prop. 1). |

## Functions

| Name | Summary |
|---|---|
| [`fit_concession_curve`](fit_concession_curve.md) | Fit the tanh concession model to a sequence of a party's successive offer *values* (in the order made). |
| [`loglog_regret_slope`](loglog_regret_slope.md) | Fit the log–log slope of cumulative regret. |
| [`no_regret_trend_test`](no_regret_trend_test.md) | Park trend test on a per-turn regret series (r_t >= 0, surplus-loss units). |
