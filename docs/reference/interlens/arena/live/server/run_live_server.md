# `run_live_server`

Serve live play until interrupted — bind, print the banner (including the `ssh -L` line, reusing `viz.serve.serve_banner`'s form), then block in `serve_forever`.

```python
run_live_server(
	provider: ScenarioProvider,
	host: str = DEFAULT_HOST,
	port: int = 0,
	run_dir=None,
) -> None
```

Defined in [`interlens.arena.live.server`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/server.py#L314-L331)

`Ctrl-C` shuts down and returns
normally so the CLI exits 0, and stops any session still running first.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `provider` | [ScenarioProvider](../provider/ScenarioProvider.md) | *required* |  |
| `host` | `str` | `DEFAULT_HOST` |  |
| `port` | `int` | `0` |  |
| `run_dir` |  | `None` |  |
