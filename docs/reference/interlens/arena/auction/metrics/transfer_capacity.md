# `transfer_capacity`

Per-seat room to make a side payment: stage budget minus the auction payment already owed.

```python
transfer_capacity(out: StageOutcome) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L395-L404)

The denominator split the transfer-usage rate must be reported against. A declared transfer executes only
against this, so a seat with no capacity did not decline to pay -- it could not, and the two are different
findings. It bites by design: the Che-Gale budget-bound seat carries `budget_mult` 0.70 and can be left
with a capacity in the twenties after winning a lot.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
