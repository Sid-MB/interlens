# `derangement`

A seeded permutation of `0..n-1` with NO fixed point: `perm[i] != i` for every `i`.

```python
derangement(n: int, seed: int) -> tuple[int, ...]
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L827-L840)

Drawn by rejection from :class:`numpy.random.Generator`, which terminates almost surely (the derangement
share of permutations tends to `1/e`). A fixed point would leave one seat holding its own card, which
would make X1 a partial control on that seat -- the one failure mode the control cannot tolerate, since
G2(b) reads a cross-persona dispersion that a single un-scrambled seat would inflate.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n` | `int` | *required* |  |
| `seed` | `int` | *required* |  |
