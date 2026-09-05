# `utilitarian_index`

Discrete **utilitarian solution**: the IR deal maximizing the surplus sum `sum_i x_i(d)` [harsanyi1955].

```python
utilitarian_index(U: np.ndarray, tau: np.ndarray) -> tuple[int, tuple[int, ...], str]
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L257-L269)

**NOT scale invariant** -- rescaling one party's sheet reweights the sum, so it is only meaningful on a shared
or normalized scale (ANAC/GENIUS normalize to [0,1] first). The IR filter matters (a below-threshold party
makes the sum meaningless); the `tau`-shift alone does not move the argmax.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
