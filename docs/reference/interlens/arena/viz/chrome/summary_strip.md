# `summary_strip`

The whole episode in one row: did it close, how good was it, how far from the normative anchor, who was left below their threshold, how much of it the engine fabricated, how long it ran, what it cost.

```python
summary_strip(payload: dict) -> str
```

Defined in [`interlens.arena.viz.chrome`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/chrome.py#L211-L248)

Replaces the old grid of tiles. Same numbers, a fifth of the vertical space — which matters because it sits
above the chart, and the chart is what a reader came for.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
