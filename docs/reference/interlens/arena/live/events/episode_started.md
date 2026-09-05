# `episode_started`

An episode began.

```python
episode_started(episode_id: str) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L147-L150)

The client fetches `/api/session/{sid}/state` for the initial payload rather than
receiving it here — the first payload carries the whole game geometry and is far too large for one frame.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode_id` | `str` | *required* |  |
