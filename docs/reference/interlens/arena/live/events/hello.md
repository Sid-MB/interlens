# `hello`

Stream opened.

```python
hello(sid: str, seq: int, phase: str, occupants: dict) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L132-L136)

`sid` is the session, `seq` the last sequence number the session has emitted (0 before
anything), `phase` where the session is (`"lobby"` | `"running"` | `"awaiting_human"` | `"done"`),
and `occupants` the current seat -> occupant-label map so a fresh page can badge seats immediately.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sid` | `str` | *required* |  |
| `seq` | `int` | *required* |  |
| `phase` | `str` | *required* |  |
| `occupants` | `dict` | *required* |  |
