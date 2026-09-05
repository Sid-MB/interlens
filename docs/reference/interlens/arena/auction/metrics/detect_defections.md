# `detect_defections`

Seats that DEFECTED at the stage after `agreement`: a party to it bidding above the level the agreement implied, operationalized as its shortfall against its own benchmark falling back to `theta` or below on the same lot (design.md §5.2 item 2).

```python
detect_defections(
	agreement: Agreement,
	nxt: StageOutcome,
	*,
	theta: float = DEFAULT_THETA,
) -> list[int]
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L529-L541)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agreement` | [Agreement](Agreement.md) | *required* |  |
| `nxt` | [StageOutcome](StageOutcome.md) | *required* |  |
| `theta` | `float` | `DEFAULT_THETA` |  |
