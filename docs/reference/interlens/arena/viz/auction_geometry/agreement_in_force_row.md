# `agreement_in_force_row`

:func:`~interlens.arena.auction.metrics.detect_agreement`'s rule applied to a STORED stage row instead of a live `StageOutcome` — whether an agreement was in force at the stage this row records.

```python
agreement_in_force_row(row: dict, *, theta: float, min_suppressors: int = 2) -> bool
```

Defined in [`interlens.arena.viz.auction_geometry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L603-L626)

The two are the same rule against two different inputs. `detect_agreement` runs inside the scenario, where
the full bid and benchmark matrices are live; a stored episode keeps only the aggregate row (`revenue`,
`benchmark_revenue`, `suppression_per_seat`, `winner_of`), which is all a post-hoc reader has. It
lives here rather than in `metrics` because reading stored records is what this layer does — but it is the
same rule, and a detector that drifted from the one the analysis counts would make the band the ladder
shades a picture of a different event.

Returns `False` for a stage with no winner, and for one whose benchmark revenue is undefined (a real state
on an on-path multi-lot benchmark) — an absent benchmark cannot support the claim that the price fell below
it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `row` | `dict` | *required* |  |
| `theta` | `float` | *required* |  |
| `min_suppressors` | `int` | `2` |  |
