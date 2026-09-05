# `episode_advice`

One episode's advised turns from the trace, keyed by turn index as a string.

```python
episode_advice(trace: dict | None, episode_id: str | None) -> dict[str, dict]
```

Defined in [`interlens.arena.viz.advice`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/advice.py#L101-L122)

Reads an inline `episodes` map or, on a sharded trace, the one shard for this episode. Returns an empty
dict for an episode the trace does not cover — an unadvised arm, an episode that errored, a run with no
sidecar, or a shard that has gone missing — which is what makes every caller a no-op rather than a special
case, and what keeps one absent shard from costing the whole render.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `trace` | `dict \| None` | *required* |  |
| `episode_id` | `str \| None` | *required* |  |
