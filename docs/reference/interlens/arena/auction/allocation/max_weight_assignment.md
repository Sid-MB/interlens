# `max_weight_assignment`

Maximum-weight assignment of rows to distinct columns: `(column_per_row, total_value)`.

```python
max_weight_assignment(value: np.ndarray) -> tuple[np.ndarray, float]
```

Defined in [`interlens.arena.auction.allocation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L111-L116)

The
maximization face of :func:`_min_cost_assignment` (it negates the matrix).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `value` | `np.ndarray` | *required* |  |
