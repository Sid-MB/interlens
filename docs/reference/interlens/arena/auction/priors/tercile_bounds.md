# `tercile_bounds`

The two public tercile boundaries of `N(0, sigma^2)`: `(-0.4307*sigma, +0.4307*sigma)`.

```python
tercile_bounds(sigma: float) -> tuple[float, float]
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L76-L79)

A
degenerate `sigma = 0` (the IPV switch) returns `(0.0, 0.0)`, so every draw renders `"typical"`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sigma` | `float` | *required* |  |
