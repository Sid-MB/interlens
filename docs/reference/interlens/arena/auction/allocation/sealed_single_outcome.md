# `sealed_single_outcome`

Settle a ONE-lot sealed auction: `(winner_seat_or_None, price)`.

```python
sealed_single_outcome(
	bids,
	*,
	pricing: str,
	tie_break,
	reserve: int = 0,
) -> tuple[int | None, int]
```

Defined in [`interlens.arena.auction.allocation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L356-L373)

The highest bid at or above `reserve` wins; ties are resolved by position in `tie_break` (the stage's
seeded seat permutation, announced before bidding). Under `"second_price"` the winner pays the
second-highest bid floored at the reserve [vickrey1961]; under `"first_price"` it pays its own bid. A
bid of `None` is a seat that took no priced action and is excluded from both the win and the price.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bids` |  | *required* |  |
| `pricing` | `str` | *required* |  |
| `tie_break` |  | *required* |  |
| `reserve` | `int` | `0` |  |
