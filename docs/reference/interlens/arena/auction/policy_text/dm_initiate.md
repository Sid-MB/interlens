# `dm_initiate`

The proposal this seat opens with, addressed to the rival whose PUBLIC profile most contests its best lot -- a public-prior computation, so the address itself leaks nothing about which lots it privately values.

```python
dm_initiate(
	*,
	instance_id: str,
	seat: int,
	stage: int,
	threat_seat: str,
	fit_lot: str,
	counter_lots,
	transfer_amount: int | None = None,
) -> str
```

Defined in [`interlens.arena.auction.policy_text`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/policy_text.py#L161-L170)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance_id` | `str` | *required* |  |
| `seat` | `int` | *required* |  |
| `stage` | `int` | *required* |  |
| `threat_seat` | `str` | *required* |  |
| `fit_lot` | `str` | *required* |  |
| `counter_lots` |  | *required* |  |
| `transfer_amount` | `int \| None` | `None` |  |
