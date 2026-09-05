# `sparsity`

Fraction of option cells (over all sheets, issues, options) whose value is exactly zero -- the score-sheet sparsity descriptor of the TMLR reproduction [reproB_tmlr] (their games run 23.7-43.0%).

```python
sparsity(sheets: tuple[ScoreSheet, ...] | list[ScoreSheet]) -> float
```

Defined in [`interlens.arena.negotiation.sheets`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L357-L368)

Zero
options are the `don't care` slots that create logrolling room and Pareto-dominated-but-acceptable deals.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sheets` | tuple[[ScoreSheet](ScoreSheet.md), ...] \| list[[ScoreSheet](ScoreSheet.md)] | *required* |  |
