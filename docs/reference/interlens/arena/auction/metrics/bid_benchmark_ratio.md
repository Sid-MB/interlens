# `bid_benchmark_ratio`

`bid / benchmark_bid` over the cells where BOTH a priced action and a benchmark bid exist.

```python
bid_benchmark_ratio(out: StageOutcome) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L180-L194)

This — not `bid_value_ratio` — is the quantity G3 pins at 1.000 for a computable seat. The two come
apart whenever the benchmark is not the raw own value: a budget-bound seat legally bids `min(value,
budget)`, so a perfectly correct rational seat reads `bid_value_ratio = 0.91` on the single-lot bank
while its `bid_benchmark_ratio` is exactly 1.000.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
