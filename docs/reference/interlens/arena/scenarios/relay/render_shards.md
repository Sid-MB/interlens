# `render_shards`

Render the per-seat private shard text for a framing.

```python
render_shards(payload: dict, framing: str, names: list[str]) -> dict
```

Defined in [`interlens.arena.scenarios.relay`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L311-L345)

Pure function of
the instance's numeric payload — every framing shows the SAME numbers.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
| `framing` | `str` | *required* |  |
| `names` | `list[str]` | *required* |  |
