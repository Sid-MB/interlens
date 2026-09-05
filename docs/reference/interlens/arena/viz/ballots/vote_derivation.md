# `vote_derivation`

The optional per-turn re-derivation sidecar for a run, or `None` when it is absent or unreadable.

```python
vote_derivation(run_root: str | Path | None) -> dict | None
```

Defined in [`interlens.arena.viz.ballots`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/ballots.py#L72-L86)

Unreadable is treated as absent on purpose: a malformed sidecar must cost the page one optional column, not
the whole render.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `run_root` | `str \| Path \| None` | *required* |  |
