# `porter_zona_rows`

One row per LOSING bid, the input to the Porter-Zona bid-rationality regression [porter_zona1993, pp. 526-533].

```python
porter_zona_rows(
	out: StageOutcome,
	*,
	attribute_score=None,
	key: dict | None = None,
) -> list[dict]
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L686-L704)

Each row carries the dependent variable (the losing bid) and the observable covariates the regression
tests it against: the seat's own realized value, its public attribute score for that lot, and its budget.
A ring member's losing bids stop tracking its own value; a genuine competitor's do not, so the test is a
comparison of FIT (against the matched silent cell, and across stages within a cell) rather than of any
single coefficient.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
| `attribute_score` |  | `None` |  |
| `key` | `dict \| None` | `None` |  |
