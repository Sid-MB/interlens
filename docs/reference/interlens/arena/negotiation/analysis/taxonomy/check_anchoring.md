# `check_anchoring`

Rigid extreme anchoring: a party makes >=2 offers whose own-surplus barely moves (range below 5% of its feasible scale) or fits a near-vertical/degenerate concession curve.

```python
check_anchoring(game, view, annotation) -> CategoryResult
```

Defined in [`interlens.arena.negotiation.analysis.taxonomy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/taxonomy.py#L189-L207)

Read from the concession fits.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `view` |  | *required* |  |
| `annotation` |  | *required* |  |
