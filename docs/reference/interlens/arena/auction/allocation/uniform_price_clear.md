# `uniform_price_clear`

Clear a uniform-price sale of `supply` identical units: `(units_won_per_bidder, clearing_price)`.

```python
uniform_price_clear(
	schedules,
	*,
	supply: int,
	tie_break,
	reserve: int = 0,
) -> tuple[np.ndarray, int]
```

Defined in [`interlens.arena.auction.allocation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L376-L394)

`schedules[i]` is bidder `i`'s weakly-decreasing per-unit bid vector. All unit bids at or above
`reserve` are pooled and ranked; the top `supply` win, and every winner pays the HIGHEST REJECTED bid
per unit (the reserve when nothing is rejected). Ties at the margin are resolved by position in
`tie_break`. Shading the inframarginal units to move this price down is exactly the demand reduction of
[ausubel_cramton2014, pp. 1370-1378].

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `schedules` |  | *required* |  |
| `supply` | `int` | *required* |  |
| `tie_break` |  | *required* |  |
| `reserve` | `int` | `0` |  |
