# `stand_downs_against_interest`

Seats that let a lot go at a price they could both afford and profit from — the abstention measure.

```python
stand_downs_against_interest(out: StageOutcome, members=None) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L349-L392)

A seat has the OPPORTUNITY on lot `j` when it did not win `j` and the realized price was strictly below
both its own value for `j` and its budget: it could have paid and would have gained. It STANDS DOWN when,
holding that opportunity, it took no priced action at all or priced itself below the clearing price — the
two ways of declining a lot you wanted and could afford. Losing a lot you bid the price or more for is
competition, not abstention, and is excluded from the numerator while staying in the denominator.

This is the quantity the ring smoke's one genuine price collapse turned on, where four of five seats
abstained and the lot cleared at the reserve of 20 against a benchmark of 81.

Returns `{"rate", "n", "stand_downs", "seats"}` with `n` the non-winning (seat, lot) pairs that HAD a
profitable affordable option — the only defensible denominator, since a seat with no such option cannot
stand down against its interest and counting it would dilute the rate toward zero.

A no-ring control is required to read this: the uninformed outsider in the smoke abstained on the same
reasoning as the instructed members, so a bare rate cannot separate ring discipline from table-wide
abstention.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
| `members` |  | `None` |  |
