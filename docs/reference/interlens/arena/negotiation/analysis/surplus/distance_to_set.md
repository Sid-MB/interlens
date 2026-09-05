# `distance_to_set`

Minimum Euclidean distance from `x` to any vector in `points` (0 if `x` is one of them).

```python
distance_to_set(x: Vec, points: Sequence[Vec], *, scale: Vec | None = None) -> float
```

Defined in [`interlens.arena.negotiation.analysis.surplus`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/surplus.py#L96-L101)

Used for
distance-to-Pareto-frontier: how far the realized outcome sits from the efficient set.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` | `Vec` | *required* |  |
| `points` | `Sequence[Vec]` | *required* |  |
| `scale` | `Vec \| None` | `None` |  |
