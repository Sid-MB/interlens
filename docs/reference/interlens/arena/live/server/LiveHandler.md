# `LiveHandler`

One request.

```python
LiveHandler()
```

Defined in [`interlens.arena.live.server`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/server.py#L82-L291)

**Inherits from:** `BaseHTTPRequestHandler`

Dispatches the route table above against the server's `SessionManager`.

The manager and the provider hang off the server object (set by :func:`make_live_server`) rather than off the
handler, since a handler instance lives for exactly one request.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `manager` | [SessionManager](../session/SessionManager.md) | The server's one session registry. |
| `protocol_version` |  |  |
| `server_version` |  |  |

## Methods {#methods}

## `do_GET` {#do_GET}

```python
do_GET(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/server.py#L99-L123)

Serve the two pages, the snapshot, and the event stream.

## `do_POST` {#do_POST}

```python
do_POST(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/server.py#L125-L153)

Handle a lobby edit, a start, a human move, a swap, a stop, or a reset.

## `log_message` {#log_message}

```python
log_message(self, fmt: str, *args=()) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/server.py#L288-L291)

Quiet by default: an SSE stream plus a per-turn poll would otherwise fill the terminal the operator is watching the game in.

Routed through the module logger at debug level instead.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `fmt` | `str` | *required* |  |
| `args` |  | `()` |  |
