# `kalai_smorodinsky_index`

Discrete **Kalai-Smorodinsky solution**: the Pareto-optimal IR deal maximizing the minimum normalized surplus `min_i x_i(d)/b_i` (`b` = ideal point over IR), refined by leximin over the normalized surplus vector [ks1975].

```python
kalai_smorodinsky_index(
	U: np.ndarray,
	tau: np.ndarray,
) -> tuple[int, tuple[int, ...], str]
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L222-L239)

**Exactly scale invariant** (`a_i` cancels in `x_i/b_i`). Original is 2-player: for
`n>2` KS can miss Pareto optimality and no solution keeps all its axioms, so we take the Pareto-restricted
max-min-normalized point with leximin ties [roth1979]; non-convex/finite cover [conley_wilkie1991]. Empty IR
set falls back to Maximum Nash Welfare.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
