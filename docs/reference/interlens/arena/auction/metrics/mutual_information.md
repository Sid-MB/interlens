# `mutual_information`

Plug-in mutual information `I(X;Y)` in nats between two DISCRETE label arrays, from the empirical joint.

```python
mutual_information(x, y) -> float
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L602-L620)

Zero when either variable is constant.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` |  | *required* |  |
| `y` |  | *required* |  |
