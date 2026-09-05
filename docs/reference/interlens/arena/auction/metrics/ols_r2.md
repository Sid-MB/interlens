# `ols_r2`

Ordinary-least-squares fit of `y_key` on `x_keys` plus an intercept, returning `{"r2", "coef", "n"}`.

```python
ols_r2(rows, *, y_key: str = 'bid', x_keys=('own_value', 'attr_score', 'budget')) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L707-L719)

Plain `numpy.linalg.lstsq`, so the Porter-Zona lane needs no new dependency; the quantity the
test reads is `r2`, whose DEGRADATION relative to a matched cell is the ring signature.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rows` |  | *required* |  |
| `y_key` | `str` | `'bid'` |  |
| `x_keys` |  | `('own_value', 'attr_score', 'budget')` |  |
