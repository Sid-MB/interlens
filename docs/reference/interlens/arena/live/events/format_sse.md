# `format_sse`

Format one event as an SSE frame, ready to write to the socket.

```python
format_sse(seq: int, event: str, data: dict) -> bytes
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L112-L125)

`seq` becomes the frame's `id:` (the value a reconnecting client echoes in `Last-Event-ID`), `event`
its type — one of the constants above — and `data` its JSON body, dumped with `ensure_ascii=False`
because the transcript is UTF-8 prose that would otherwise triple in size as escapes. The body is one line by
construction: `json.dumps` escapes every newline inside a string, and a literal newline in `data` would
be read as a field break and split one event into two. `default=str` keeps a stray non-JSON value (a Path
on a provenance field) from taking the stream down mid-game.

Returns bytes because this is written straight to a socket, not to a text stream.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seq` | `int` | *required* |  |
| `event` | `str` | *required* |  |
| `data` | `dict` | *required* |  |
