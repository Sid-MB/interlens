# `auction_summary_strip`

The whole auction episode in one row: the format, how efficient it was, what it raised against benchmark, whether anything was suppressed, and how much of it was model behaviour at all.

```python
auction_summary_strip(payload: dict) -> str
```

Defined in [`interlens.arena.viz.auction_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_page.py#L525-L569)

The negotiation strip's fields (deal / distance to NBS / Gini / below-τ) have no auction analogue and are
replaced rather than reinterpreted; :func:`~interlens.arena.viz.chrome.stat` is shared.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
