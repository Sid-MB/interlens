# `overbid_own_value`

The `overbid_own_value_rate` over priced actions, split `punitive` (the bidder did not win) and `acquisitive` (it did).

```python
overbid_own_value(out: StageOutcome) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L256-L278)

The split is not cosmetic: punitive overbidding is near-free in second-price/English and expensive in
Dutch, so pooling the two would make the same number mean different things across the format contrast
(design.md §3.2).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
