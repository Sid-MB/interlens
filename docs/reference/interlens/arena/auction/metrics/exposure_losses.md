# `exposure_losses`

Seats that won part but not all of their synergy target set, and the surplus they lost by it.

```python
exposure_losses(out: StageOutcome) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L294-L300)

The
countable form of "bidding on the set and winning only part of it is a live risk" (design.md §2.2).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
