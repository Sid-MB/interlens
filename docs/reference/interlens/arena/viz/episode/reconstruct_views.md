# `reconstruct_views`

Re-derive each turn's rendered view by deterministic replay, for episodes recorded before the per-turn `view` field existed.

```python
reconstruct_views(episode: dict, instance: dict) -> dict[int, list[dict]]
```

Defined in [`interlens.arena.viz.episode`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/episode.py#L419-L450)

Feeds the stored turns back through the scenario's state machine (`arena.replay`) and captures the
`SeatRequest.view` the machine builds for each one. Exact for the state, but the prompt TEXT comes from
today's prompt code — so a reconstructed view is what the current build would show a seat at that state, not a
byte-guaranteed record of what the model saw, and the page labels it accordingly.

One difference is systematic rather than a drift risk, and the caller marks it separately (see
:data:`RETRY_SOURCE`): when a seat's malformed response triggered the engine's one retry, the LIVE retry view
carried the failed attempt plus a repair instruction, while replay re-issues the original request. A retry
turn's reconstruction is therefore the FIRST attempt's prompt; the repair text is not recoverable from the
record.

Returns `{}` on any failure (unknown scenario, prompt/state drift), because a missing prompt panel is a far
better outcome than a crashed export.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `instance` | `dict` | *required* |  |
