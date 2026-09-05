# `episode_done`

The episode ended.

```python
episode_done(status: str, outcome: dict, final: dict | None = None) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L225-L229)

`status` is the episode's own (`"done"` / `"error"`) or a live-play reason
(`"stopped"`, `"budget_stopped"`); `outcome` is the scenario's outcome record; `final` is an optional
closing payload slice (scores, the agreed deal) for the summary strip without a second fetch.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `status` | `str` | *required* |  |
| `outcome` | `dict` | *required* |  |
| `final` | `dict \| None` | `None` |  |
