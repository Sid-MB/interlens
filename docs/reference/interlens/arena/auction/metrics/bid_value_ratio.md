# `bid_value_ratio`

`bid / own_value` at the decision point, over seats that took a priced action.

```python
bid_value_ratio(out: StageOutcome) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L156-L177)

Returns `{"mean", "n", "never_bid_rate", "never_bid_n", "per_seat"}`. `never_bid_rate` is reported
separately and never folded in as ratio 0 — the denominator rule that keeps a silent seat from looking
like a maximally shading one.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
