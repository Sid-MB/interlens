# `attribute_score`

The public affinity matrix `(n_bidders, n_items)` of dot products `a_i . w_j`.

```python
attribute_score(attrs: np.ndarray, loadings: np.ndarray) -> np.ndarray
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L206-L211)

This is the entire public signal about the SHAPE of a bidder's valuation curve: everything else in the
value equation is either a public scalar (`B_jt`, `beta`) or a private draw.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `attrs` | `np.ndarray` | *required* |  |
| `loadings` | `np.ndarray` | *required* |  |
