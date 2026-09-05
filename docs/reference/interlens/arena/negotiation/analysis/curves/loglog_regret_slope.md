# `loglog_regret_slope`

Fit the log–log slope of cumulative regret.

```python
loglog_regret_slope(per_turn_regret) -> LogLogRegret
```

Defined in [`interlens.arena.negotiation.analysis.curves`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/curves.py#L198-L216)

Returns `nan` slope if fewer than 2 turns have positive
cumulative regret (a flat zero-regret series is trivially sublinear but the slope is unidentified).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `per_turn_regret` |  | *required* |  |
