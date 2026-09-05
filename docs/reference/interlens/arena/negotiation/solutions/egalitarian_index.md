# `egalitarian_index`

Discrete **egalitarian (Kalai proportional) solution**: the IR deal maximizing `min_i x_i(d)`, leximin refined [kalai1977].

```python
egalitarian_index(U: np.ndarray, tau: np.ndarray) -> tuple[int, tuple[int, ...], str]
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L242-L254)

**NOT scale invariant** -- it presupposes interpersonal utility comparability (in the
title of the paper), so on arbitrary private scales the raw egalitarian point is meaningless across parties;
on normalized surpluses `x_i/b_i` it collapses into KS. Only interpret it when the sheets share a scale by
design (e.g. a common 0-100 budget).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
