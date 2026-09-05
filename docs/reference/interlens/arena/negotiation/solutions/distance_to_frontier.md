# `distance_to_frontier`

Euclidean distance, in normalized-surplus space, from deal `index` to the nearest Pareto-frontier deal (0 iff `index` is itself Pareto-optimal).

```python
distance_to_frontier(U: np.ndarray, tau: np.ndarray, index: int) -> float
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L310-L317)

Scale-invariant. This is the centipawn-loss-style denominator for
per-turn divergence: how far a chosen deal sits below the efficient frontier.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
| `index` | `int` | *required* |  |
