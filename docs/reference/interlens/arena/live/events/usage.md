# `usage`

Spend so far against the cap.

```python
usage(
	tokens_in: int,
	tokens_out: int,
	cost_usd: float,
	cap_usd: float | None,
	exhausted: bool,
) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L217-L222)

`cap_usd` is `None` for a session with no metered seat; `exhausted`
means the meter has stopped the run, which the client should read as the episode being over.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tokens_in` | `int` | *required* |  |
| `tokens_out` | `int` | *required* |  |
| `cost_usd` | `float` | *required* |  |
| `cap_usd` | `float \| None` | *required* |  |
| `exhausted` | `bool` | *required* |  |
