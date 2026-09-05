# `error`

Something failed.

```python
error(message: str, fatal: bool = False) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L232-L235)

`fatal=True` means the session cannot continue and the page should stop waiting for
turns; `False` means one action failed and the game is still live.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `str` | *required* |  |
| `fatal` | `bool` | `False` |  |
