# `serve_directory`

Serve `directory` over HTTP until interrupted — bind, print :func:`serve_banner`, then block in `serve_forever`.

```python
serve_directory(directory: str | Path, port: int = 0, host: str = DEFAULT_HOST) -> None
```

Defined in [`interlens.arena.viz.serve`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/serve.py#L77-L89)

`Ctrl-C` (`KeyboardInterrupt`) shuts the server down and returns normally rather than
raising, so the CLI exits 0. See :func:`make_server` for `port` / `host`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `directory` | `str \| Path` | *required* |  |
| `port` | `int` | `0` |  |
| `host` | `str` | `DEFAULT_HOST` |  |
