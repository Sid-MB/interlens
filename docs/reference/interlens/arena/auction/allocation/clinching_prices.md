# `clinching_prices`

Run the Ausubel ascending clock on `supply` identical units [ausubel2004, pp. 1454-1460].

```python
clinching_prices(
	schedules,
	*,
	supply: int,
	increment: int = 1,
	reserve: int = 0,
) -> tuple[np.ndarray, np.ndarray]
```

Defined in [`interlens.arena.auction.allocation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L397-L429)

`schedules[i]` is bidder `i`'s weakly-decreasing per-unit marginal value/bid vector; its demand at
clock price `p` is the number of entries worth STRICTLY MORE than `p` (a bidder willing to pay `v`
leaves as the clock passes `v`). The strictness is what makes the discrete clock reproduce the Vickrey
payment exactly rather than overcharging by one increment, which the tests check against a hand-computed
example. Whenever residual rival demand falls below supply, bidder `i` CLINCHES the shortfall at the
current clock price, and the clock keeps rising until aggregate demand no longer exceeds supply. Returns
`(units_won, total_payment)`.

The point of the rule is that the price a bidder pays for a unit is set by the moment its rivals' demand
receded, not by its own later bidding — which is why truthful demand is an equilibrium and the
demand-reduction incentive of the uniform-price rule disappears.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `schedules` |  | *required* |  |
| `supply` | `int` | *required* |  |
| `increment` | `int` | `1` |  |
| `reserve` | `int` | `0` |  |
