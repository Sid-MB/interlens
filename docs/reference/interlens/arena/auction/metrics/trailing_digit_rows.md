# `trailing_digit_rows`

Rows `{seat, item, digit, target_item}` for the code-bidding test [cramton_schwartz2000, pp. 236-244]: the trailing digit of each bid against a uniform null, and its regression on the seat's own target-slot index.

```python
trailing_digit_rows(out: StageOutcome, *, key: dict | None = None) -> list[dict]
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L722-L735)

Run per stage and tested for a TREND across stages rather than a level (design.md
§9.3).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
| `key` | `dict \| None` | `None` |  |
