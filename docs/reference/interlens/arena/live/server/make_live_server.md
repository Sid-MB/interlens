# `make_live_server`

Bind (but do not run) the live-play server over `provider`.

```python
make_live_server(
	provider: ScenarioProvider,
	host: str = DEFAULT_HOST,
	port: int = 0,
	run_dir=None,
) -> ThreadingHTTPServer
```

Defined in [`interlens.arena.live.server`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/server.py#L294-L311)

`port=0` asks the OS for a free ephemeral port; read the one chosen back off `server.server_address[1]`.
`run_dir` is where episodes are written (a temporary directory when omitted — but a session whose episodes
are worth keeping should be given a real one, since the JSON on disk is the durable artifact and the stream
is only a view of it).

Returns the bound server so the caller decides how to run it: `serve_forever()` on this thread, or another
one in a test. Call `server_close()` when done.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `provider` | [ScenarioProvider](../provider/ScenarioProvider.md) | *required* |  |
| `host` | `str` | `DEFAULT_HOST` |  |
| `port` | `int` | `0` |  |
| `run_dir` |  | `None` |  |
