# `efficiency`

`realized_welfare / max_feasible_welfare`.

```python
efficiency(out: StageOutcome) -> float
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L138-L141)

A stage with no sale scores 0, never "excluded"
(design.md §5.1). A degenerate zero-welfare stage scores 0.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
