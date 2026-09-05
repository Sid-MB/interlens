# `euclidean`

Euclidean distance `||x - y||` in surplus space, optionally after dividing each coordinate by a per-party `scale` (e.g. that party's max feasible surplus) so parties on different point scales are commensurable.

```python
euclidean(x: Vec, y: Vec, *, scale: Vec | None = None) -> float
```

Defined in [`interlens.arena.negotiation.analysis.surplus`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/surplus.py#L88-L93)

With `scale=None` distances are in raw surplus units.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` | `Vec` | *required* |  |
| `y` | `Vec` | *required* |  |
| `scale` | `Vec \| None` | `None` |  |
