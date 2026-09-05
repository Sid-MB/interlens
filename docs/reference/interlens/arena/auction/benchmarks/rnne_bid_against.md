# `rnne_bid_against`

The risk-neutral first-price equilibrium bid for a bidder of type `value` facing rivals with the given value distributions [riley_samuelson1981, pp. 383-385]:

```python
rnne_bid_against(
	value: float,
	rival_pmfs,
	*,
	lower: float = 0.0,
	n_grid: int = 400,
) -> float
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L193-L215)

```python
b(v) = v - integral_{lower}^{v} G(x) dx / G(v),    G(x) = prod_k F_k(x)
```

Solved numerically by trapezoid quadrature on a grid between `lower` and `value`, so it applies to
the design's lognormal-shaped value distributions with no closed form. It is the EXACT equilibrium when
the bidders are symmetric — the test suite checks it reproduces `(n-1)/n * v` on the uniform case — and
a monotone, well-defined one-step approximation when they are not (the exact asymmetric equilibrium is a
boundary-value ODE system with no closed form, and iterated best response on the integer bid grid pools
at the top rather than converging, so it is deliberately not used).

`G(v) = 0` (a type below every rival's support, which can only lose) returns `lower`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `value` | `float` | *required* |  |
| `rival_pmfs` |  | *required* |  |
| `lower` | `float` | `0.0` |  |
| `n_grid` | `int` | `400` |  |
