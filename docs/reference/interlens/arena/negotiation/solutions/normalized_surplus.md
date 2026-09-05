# `normalized_surplus`

Per-deal nonnegative normalized surplus `clip(x_i, 0) / b_i` (`b_i` = ideal over all deals), the scale-invariant coordinate the distance metrics live in.

```python
normalized_surplus(U: np.ndarray, tau: np.ndarray) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L296-L307)

Below-threshold "gains" are clipped to 0 so they do
not count as progress.

Public because it is the ONE coordinate system in which deals are compared across parties on arbitrary
private scales: the distance metrics below and the frontier visualizer (`arena.viz`) must plot in the same
space, so they share this function rather than each re-deriving a normalizer.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
