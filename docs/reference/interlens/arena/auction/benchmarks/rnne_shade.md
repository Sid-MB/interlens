# `rnne_shade`

The symmetric risk-neutral first-price shading factor `(n-1)/n` — `0.8` at the design's five seats [riley_samuelson1981, pp. 383-385].

```python
rnne_shade(n_bidders: int) -> float
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L166-L170)

Exact for uniformly distributed IPV values; the design scores Dutch
claim prices against it (design.md §3.3).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_bidders` | `int` | *required* |  |
