# `budget_violations`

Bids above the seat's stage budget, and payments the seat cannot cover.

```python
budget_violations(out: StageOutcome) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L303-L311)

A bid above budget is a
LEGALITY error (payments must be collectible) rather than an economic one, so it is counted separately
from :func:`overbid_own_value` (design.md §3.2).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
