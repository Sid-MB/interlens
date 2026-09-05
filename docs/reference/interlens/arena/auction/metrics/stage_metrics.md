# `stage_metrics`

Every stage-level metric of design.md §5.1 for one stage, flattened into one dict with each conditional metric's denominator alongside it.

```python
stage_metrics(out: StageOutcome) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L422-L462)

The single call an analyzer makes per stage row.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
