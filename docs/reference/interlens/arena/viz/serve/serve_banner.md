# `serve_banner`

The startup message: where the pages are, the URL to open, and — because the reader is usually on a cluster node with no browser — the exact `ssh -L` command to forward `port` to their laptop, with this machine's real hostname already filled in.

```python
serve_banner(directory: str | Path, port: int, host: str = DEFAULT_HOST) -> str
```

Defined in [`interlens.arena.viz.serve`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/serve.py#L56-L74)

Returned as a string rather than printed so it is testable.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `directory` | `str \| Path` | *required* |  |
| `port` | `int` | *required* |  |
| `host` | `str` | `DEFAULT_HOST` |  |
