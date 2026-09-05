# `dm_graph`

The directed message graph over the seats, with a stage scrubber and the per-dyad counts beside it.

```python
dm_graph(auction: dict, payload: dict) -> str
```

Defined in [`interlens.arena.viz.auction_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_page.py#L380-L465)

Edge width is the message count and the scrubber restricts the graph to one stage at a time (every stage's
edges are in the document; the browser only changes which are visible, so the panel still reads with
scripting off). Beside it sits the per-dyad table with the coordination-talk screen's hit count.

What is deliberately NOT here is per-dyad mutual information with a permutation p-value. That estimate is
cell-level: it needs the whole cell's stages, and computing it over one episode's six would be noise
wearing a p-value. The campaign hub carries it, beside these counts, at the level it is defined at.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `auction` | `dict` | *required* |  |
| `payload` | `dict` | *required* |  |
