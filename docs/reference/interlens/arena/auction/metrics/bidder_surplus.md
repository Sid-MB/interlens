# `bidder_surplus`

Per-seat surplus `V_i(S_i) - payment_i`.

```python
bidder_surplus(out: StageOutcome) -> np.ndarray
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L150-L153)

Reported per seat AND aggregated, because a rational seat
can gain privately while aggregate welfare is flat and the aggregate alone would hide it [asker2010].

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
