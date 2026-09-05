# `auc`

Trapezoidal area under a metric's turn series, divided by the number of intervals — i.e. the TIME-MEAN of the metric, on the metric's own scale rather than an area that grows with episode length (so a 4-round and a 12-round episode are comparable).

```python
auc(series: list[float]) -> float
```

Defined in [`interlens.arena.negotiation.belief_accuracy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/belief_accuracy.py#L162-L170)

A single point returns itself; an empty series returns `0.0`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `series` | `list[float]` | *required* |  |
