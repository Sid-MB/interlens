# `winners_curse`

`negative_surplus_win_rate` — wins where the winner's bundle value falls below its payment — over all wins, split by cause: `exposure` (won part of a synergy target set, so the bundle bonus never fired) versus `common_value` (everything else, i.e. an overestimate of the common component).

```python
winners_curse(out: StageOutcome) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L281-L291)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
