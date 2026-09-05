# `no_regret_trend_test`

Park trend test on a per-turn regret series (r_t >= 0, surplus-loss units).

```python
no_regret_trend_test(per_turn_regret, *, alpha: float = 0.05) -> NoRegretTrend
```

Defined in [`interlens.arena.negotiation.analysis.curves`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/curves.py#L149-L179)

Forms cumulative regret `R_t = sum_{s<=t} r_s` then average regret `a_t = R_t/t` and runs Mann–Kendall
for a monotone decreasing trend in `a_t`. Needs >= 3 turns. Ties are corrected in the variance; a
continuity correction is applied to S.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `per_turn_regret` |  | *required* |  |
| `alpha` | `float` | `0.05` |  |
