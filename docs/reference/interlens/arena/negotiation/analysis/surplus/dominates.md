# `dominates`

`y` Pareto-dominates `x`: `y_i >= x_i` for all i and (if `strict_any`) strictly greater for at least one i.

```python
dominates(y: Vec, x: Vec, *, strict_any: bool = True) -> bool
```

Defined in [`interlens.arena.negotiation.analysis.surplus`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/surplus.py#L47-L55)

With `strict_any=False` this is weak dominance (`y_i >= x_i` for all i).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `y` | `Vec` | *required* |  |
| `x` | `Vec` | *required* |  |
| `strict_any` | `bool` | `True` |  |
