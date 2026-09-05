# `quantize`

Quantize a 1-D array into `bins` equal-frequency bins, returning integer bin labels.

```python
quantize(x, *, bins: int = DEFAULT_VALUE_BINS) -> np.ndarray
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L591-L599)

Equal
frequency rather than equal width so a skewed value distribution cannot leave a bin empty and inflate the
plug-in mutual information.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` |  | *required* |  |
| `bins` | `int` | `DEFAULT_VALUE_BINS` |  |
