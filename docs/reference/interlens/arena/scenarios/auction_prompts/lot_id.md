# `lot_id`

The addressable lot token, `L01`..`L24` -- what the action grammar's `"lot"` field carries and what every table keys on.

```python
lot_id(slot_id: int) -> str
```

Defined in [`interlens.arena.scenarios.auction_prompts`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L150-L153)

Zero-padded so lot ids sort lexicographically in a 20-lot catalogue.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `slot_id` | `int` | *required* |  |
