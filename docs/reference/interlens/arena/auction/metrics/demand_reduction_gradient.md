# `demand_reduction_gradient`

The slope of `bid / true marginal value` on unit index — the demand-reduction signature [ausubel_cramton2014, pp. 1370-1378]: a bidder shading its inframarginal units produces a NEGATIVE slope, a demand-reduction-free schedule a flat one.

```python
demand_reduction_gradient(schedule, marginal_values) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L407-L419)

Returns the slope, the per-unit ratios, and the unit count.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `schedule` |  | *required* |  |
| `marginal_values` |  | *required* |  |
