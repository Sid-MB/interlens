# `clinching_benchmark`

Truthful demand under the Ausubel clinching clock — an equilibrium of that mechanism, so unlike the uniform-price case this benchmark IS the equilibrium prediction [ausubel2004, pp. 1454-1460].

```python
clinching_benchmark(
	vm: ValueModel,
	*,
	n_units: int,
	increment: int = 1,
	reserve: int = 0,
) -> Benchmark
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L438-L452)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `vm` | [ValueModel](../allocation/ValueModel.md) | *required* |  |
| `n_units` | `int` | *required* |  |
| `increment` | `int` | `1` |  |
| `reserve` | `int` | `0` |  |
