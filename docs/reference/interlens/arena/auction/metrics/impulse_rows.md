# `impulse_rows`

Rows for the punishment impulse response over the `horizon` stages after a defection (design.md §5.2 item 3).

```python
impulse_rows(
	outcomes,
	defection_stage: int,
	defectors,
	*,
	horizon: int = IMPULSE_HORIZON,
	key: dict | None = None,
) -> list[dict]
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L562-L585)

One row per (seat, k) with the regression's variables already computed: `bid_ratio` (the seat's mean
bid/value at stage `t+k`), `defected_against` (this seat was a victim of the defection),
`own_defection` (this seat was the defector), and `own_value`. The predicted signature is
`beta_1 > 0` — rivals bid aggressively to deny the defector — decaying toward baseline at k = 2, 3
[calvano2020, pp. 3277-3288].

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `outcomes` |  | *required* |  |
| `defection_stage` | `int` | *required* |  |
| `defectors` |  | *required* |  |
| `horizon` | `int` | `IMPULSE_HORIZON` |  |
| `key` | `dict \| None` | `None` |  |
