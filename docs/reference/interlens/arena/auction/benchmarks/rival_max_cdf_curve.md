# `rival_max_cdf_curve`

`G(x) = prod_k F_k(x)` — the CDF of the highest RIVAL value — evaluated on `grid`.

```python
rival_max_cdf_curve(rival_pmfs, grid: np.ndarray) -> np.ndarray
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L178-L190)

Valid as a product because `(z_k, eps_k)` are independent across bidders (they are correlated only
across slots within a bidder), which is the sense in which the APV structure is affiliated in values but
not in types.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rival_pmfs` |  | *required* |  |
| `grid` | `np.ndarray` | *required* |  |
