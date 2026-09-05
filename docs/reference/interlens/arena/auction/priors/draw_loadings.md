# `draw_loadings`

Draw the persistent public loading matrix `w` of shape `(n_items, K)`.

```python
draw_loadings(rng: np.random.Generator, n_items: int, K: int) -> np.ndarray
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L167-L179)

Loadings are drawn WITHOUT REPLACEMENT from the `3^K - 1` non-zero vectors in `{-1, 0, +1}^K`, so no
two lots have an identical public profile (two indistinguishable lots would give a market-division
convention nothing to attach to, and would make the S1 unique-efficient-allocation screen a coin flip) and
no lot is profile-less. Whole-number loadings keep the catalogue printable and the arithmetic checkable in
a transcript.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rng` | `np.random.Generator` | *required* |  |
| `n_items` | `int` | *required* |  |
| `K` | `int` | *required* |  |
