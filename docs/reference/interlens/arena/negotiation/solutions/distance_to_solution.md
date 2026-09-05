# `distance_to_solution`

Euclidean distance, in normalized-surplus space, between deal `index` and a reference solution deal `target_index` (e.g. the NBS or KS index).

```python
distance_to_solution(
	U: np.ndarray,
	tau: np.ndarray,
	index: int,
	target_index: int,
) -> float
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L320-L326)

Scale-invariant; 0 iff the two deals give identical normalized
surplus.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
| `index` | `int` | *required* |  |
| `target_index` | `int` | *required* |  |
