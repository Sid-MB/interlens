# `stage_benchmark`

The exact equilibrium benchmark for stage `t` of `spec`, dispatching on the mechanism family.

```python
stage_benchmark(spec, t: int, *, posteriors=None, trajectory=None) -> Benchmark
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L458-L540)

Parameters
----------
spec : AuctionSpec
    The episode spec.
t : int
    1-indexed stage.
posteriors : list[RivalPosterior] | None
    Per-seat public posteriors, used only by the Dutch/first-price path under APV where the equilibrium
    is solved numerically. `None` builds them from the spec's public constants, which is what a seat
    holding only public information could do itself.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `spec` |  | *required* |  |
| `t` | `int` | *required* |  |
| `posteriors` |  | `None` |  |
| `trajectory` |  | `None` |  |
