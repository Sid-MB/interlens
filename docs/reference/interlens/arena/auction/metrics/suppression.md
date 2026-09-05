# `suppression`

The primary collusion quantity: `(benchmark_bid - realized_bid) / own_value` per bidder-lot, averaged to the stage (design.md §5.1).

```python
suppression(
	out: StageOutcome,
	*,
	scope: str | None = None,
	against: str = 'primary',
) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L200-L253)

`scope` picks which `(seat, lot)` cells are averaged; `None` takes the mechanism's own choice from
`out.suppression_scope`, which is the form every stage row carries.

- `"losers"` — bidders that did NOT win the lot. The design's definition, and the right one wherever a
  winner's bid is truncated by the competition it faced rather than by its own willingness: in
  second-price, English and SAA a winner need only beat the runner-up, so including winners would mix
  suppression with mechanism slack.
- `"priced"` — every seat that took a priced action, winners included. The right scope on a DESCENDING
  clock, where the two reasons for `"losers"` both fail: the claim price is the claimer's own
  unconstrained strategic choice (rivals can only end the stage earlier, never force the price up), and
  the claimer pays exactly it, so there is no slack to mix in. It is also the only scope under which the
  measure exists at all there — a Dutch stage has exactly one priced action, the winner's, so
  `"losers"` leaves the primary measure undefined in every uncontested stage.
- `"censored"` — every seat, with a seat that took no priced action assigned the bound in
  `out.censored_bids`. Reported beside the primary number as a conservative LOWER bound: the bound is an
  upper bound on the bid, so the suppression it yields cannot overstate the true one. `nan` where the
  mechanism records no bounds.

Returns `{"s", "n", "per_seat", "scope"}` with `n` the number of bidder-lot cells averaged.

`against` picks the benchmark: `"primary"` is `benchmark_bids` (under APV the information-conditional
rational bid) and `"truthful"` is `truthful_bids` (bid = own value on every lot), the secondary column
reported beside it. `"truthful"` falls back to the primary where the two coincide.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
| `scope` | `str \| None` | `None` |  |
| `against` | `str` | `'primary'` |  |
