# `detect_agreement`

Apply the outcome rule above to one stage and return every lot on which an agreement is in force.

```python
detect_agreement(
	out: StageOutcome,
	benchmark_prices,
	*,
	theta: float = DEFAULT_THETA,
	min_suppressors: int = 2,
) -> list[Agreement]
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L500-L526)

`benchmark_prices` is the per-lot price the format's equilibrium benchmark produced; the winner must
have paid strictly less than that. Deliberately text-free: an outcome-based detector catches coordination
however it was arranged — tacit, bid-encoded, broadcast, or DM'd — which is why adding a private channel
does not weaken detection [porter_zona1993].

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
| `benchmark_prices` |  | *required* |  |
| `theta` | `float` | `DEFAULT_THETA` |  |
| `min_suppressors` | `int` | `2` |  |
