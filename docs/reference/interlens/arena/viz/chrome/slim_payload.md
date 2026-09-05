# `slim_payload`

A copy of `payload` whose per-turn prompt views are indices into a shared `msgpool`.

```python
slim_payload(payload: dict) -> dict
```

Defined in [`interlens.arena.viz.chrome`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/chrome.py#L66-L96)

Identical `(role, content)` messages are pooled once and every view becomes a list of integers, which the
browser turns back into messages on demand (`viewOf`). Purely a transport change: the rendered page shows
exactly the same text, and any turn that carries no view keeps its `None`. Comparison payloads carry two
sides, so both are slimmed into ONE pool — the two episodes of a seat swap share a system prompt and most of
their history, which is precisely where the duplication is worst.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
