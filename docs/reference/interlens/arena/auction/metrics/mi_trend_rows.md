# `mi_trend_rows`

Rows `{stage, mi}` for the covert-code CONVERGENCE test (design.md §5.2 item 4): the per-dyad MI as a function of stage, whose slope is tested for a positive trend against a clustered permutation null.

```python
mi_trend_rows(mi_by_stage, *, key: dict | None = None) -> list[dict]
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L675-L680)

Kept as rows rather than a fitted slope so the clustering happens in the campaign's one bootstrap
estimator rather than a second one here.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `mi_by_stage` |  | *required* |  |
| `key` | `dict \| None` | `None` |  |
