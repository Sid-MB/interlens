# `pairwise_iou`

Mean pairwise Intersection-over-Union of the parties' *value supports* -- the score-function-overlap descriptor of the TMLR reproduction [reproB_tmlr] (their games run 18.8-29.8%).

```python
pairwise_iou(sheets: tuple[ScoreSheet, ...] | list[ScoreSheet]) -> float
```

Defined in [`interlens.arena.negotiation.sheets`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L371-L391)

Each party's support is the set of `(issue, option)` cells it scores with a nonzero value; for every pair
of parties IoU = `|support_a & support_b| / |support_a | support_b|`, averaged over all pairs. Low IoU =
parties care about disjoint parts of the deal (integrative, logrolling-friendly); high IoU = they fight over
the same cells (distributive).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sheets` | tuple[[ScoreSheet](ScoreSheet.md), ...] \| list[[ScoreSheet](ScoreSheet.md)] | *required* |  |
