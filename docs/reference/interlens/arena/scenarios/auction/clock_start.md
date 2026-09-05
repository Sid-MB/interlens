# `clock_start`

The clock start price used by every stage of a clock-family episode.

```python
clock_start(spec) -> int
```

Defined in [`interlens.arena.scenarios.auction`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L84-L95)

Derived from the frozen draws rather than stored: the largest per-stage `clock_ceiling` (itself set
above that stage's maximum realized valuation), rounded up onto the increment grid. One start for the
whole episode keeps the system prompt's printed clock consistent with every stage's turn view, and makes
the ceiling reachable only by a bidder bidding above every value in the stage — which is what makes
`clock_ceiling_rate` a protocol-failure statistic rather than an ordinary outcome.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `spec` |  | *required* |  |
