# `advice_trace`

The optional advice sidecar for a run, or `None` when it is absent or unreadable.

```python
advice_trace(run_root: str | Path | None) -> dict | None
```

Defined in [`interlens.arena.viz.advice`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/advice.py#L73-L98)

Two shapes are read, because one blob does not serve both arm sizes. A single-advised-seat arm's trace is a
few megabytes and ships whole, with its episodes inline. An **all-advised** arm's is tens of megabytes — every
turn is advised, so there are five times the turns and five times the claims — and is written as an index
plus one file per episode; a reader auditing one episode then fetches that episode rather than the corpus.
The index says which shape it is (`sharded`), so nothing is inferred from the presence of a key.

Unreadable is treated as absent for the same reason the ballot sidecar is: a malformed audit file must cost
the page one optional panel, not the whole render.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `run_root` | `str \| Path \| None` | *required* |  |
