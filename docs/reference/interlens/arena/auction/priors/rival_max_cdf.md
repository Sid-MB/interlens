# `rival_max_cdf`

`P(max_k v_kj <= x)` = the product of the rivals' CDFs, valid because `(z_k, eps_k)` are independent ACROSS bidders (they are correlated only across slots within a bidder).

```python
rival_max_cdf(posteriors: 'list[RivalPosterior]', slot: int, x: float) -> float
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L505-L512)

This is the
distribution every conditional-on-winning calculation and every first-price best response reads.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `posteriors` | `'list[RivalPosterior]'` | *required* |  |
| `slot` | `int` | *required* |  |
| `x` | `float` | *required* |  |
