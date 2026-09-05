# `uniform_price_benchmark`

The demand-reduction-free uniform-price outcome: every seat submits its true marginal-value schedule.

```python
uniform_price_benchmark(
	vm: ValueModel,
	*,
	n_units: int,
	tie_break,
	reserve: int = 0,
) -> Benchmark
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L416-L435)

This is deliberately NOT the uniform-price equilibrium — under uniform pricing shading the inframarginal
units is strictly optimal, so the true-value schedule is the COMPETITIVE reference against which that
shading is measured [ausubel_cramton2014, pp. 1370-1378]. The note field says so, so the number is never
read as an equilibrium prediction.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `vm` | [ValueModel](../allocation/ValueModel.md) | *required* |  |
| `n_units` | `int` | *required* |  |
| `tie_break` |  | *required* |  |
| `reserve` | `int` | `0` |  |
