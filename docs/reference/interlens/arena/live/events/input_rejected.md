# `input_rejected`

A human submission was refused before it reached the engine.

```python
input_rejected(seat: str, reason: str) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L203-L206)

`reason` is shown verbatim to the player,
so it must say what was wrong in their terms. Nothing was enqueued: the seat is still waiting.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `reason` | `str` | *required* |  |
