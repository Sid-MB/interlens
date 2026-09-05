# `lobby_state`

The lobby's full configuration: the chosen instance bank, framing and instance, the per-seat configs (`SeatConfig.to_json()` dicts, in seat order) and the session's spend cap in dollars.

```python
lobby_state(
	bank: str,
	framing: str,
	instance_id: str,
	seats: list[dict],
	budget_usd: float,
) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L139-L144)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bank` | `str` | *required* |  |
| `framing` | `str` | *required* |  |
| `instance_id` | `str` | *required* |  |
| `seats` | `list[dict]` | *required* |  |
| `budget_usd` | `float` | *required* |  |
