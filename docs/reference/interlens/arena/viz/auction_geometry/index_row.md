# `index_row`

The auction index's columns for one episode, derived from the STORED record with no replay.

```python
index_row(episode: dict, instance: dict | None = None) -> dict
```

Defined in [`interlens.arena.viz.auction_geometry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L554-L600)

The one owner of what those columns mean. Two callers need them from two different inputs and must not
disagree: :func:`~interlens.arena.viz.export._auction_fields` has a full render payload in hand and adds
the counterfactual-agreement column on top of this, while a campaign hub listing every episode in the
campaign has only the episode JSON and cannot afford a replay per row — 1,000 replays to fill a table is
minutes of work for columns that are all in the stored outcome already.

`onset` uses :mod:`interlens.arena.auction.metrics`, so the index's onset column and the survival
analysis count the same event. `difficulty` comes from the instance when one is supplied.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `instance` | `dict \| None` | `None` |  |
