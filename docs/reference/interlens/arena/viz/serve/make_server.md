# `make_server`

Bind (but do not run) an HTTP server rooted at `directory`.

```python
make_server(
	directory: str | Path,
	port: int = 0,
	host: str = DEFAULT_HOST,
) -> ThreadingHTTPServer
```

Defined in [`interlens.arena.viz.serve`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/serve.py#L42-L53)

`port` is the TCP port to listen on; `0` — the default — asks the OS for a free ephemeral port, which is
what you want when several people share a node and fixed ports collide. Read the port that was actually
chosen back off `server.server_address[1]`. `host` is the bind address (see :data:`DEFAULT_HOST`).

Returns the bound server so the caller decides how to run it: `serve_forever()` on this thread (see
:func:`serve_directory`) or on another one for a test. Call `server_close()` when done.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `directory` | `str \| Path` | *required* |  |
| `port` | `int` | `0` |  |
| `host` | `str` | `DEFAULT_HOST` |  |
