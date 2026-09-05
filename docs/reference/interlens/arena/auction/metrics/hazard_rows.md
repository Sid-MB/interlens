# `hazard_rows`

One row per AT-RISK stage transition, the input to the discrete-time defection hazard.

```python
hazard_rows(
	outcomes,
	benchmark_prices_by_stage,
	*,
	theta: float = DEFAULT_THETA,
	key: dict | None = None,
) -> list[dict]
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L544-L559)

A transition is at risk when an agreement was in force at stage `t` and stage `t+1` exists; the row
records whether any party defected. Rows carry `key` (instance/episode identifiers) unchanged so the
clustered bootstrap can resample whole instances without the estimator knowing anything about the
experiment's design (design.md §9.1).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `outcomes` |  | *required* |  |
| `benchmark_prices_by_stage` |  | *required* |  |
| `theta` | `float` | `DEFAULT_THETA` |  |
| `key` | `dict \| None` | `None` |  |
