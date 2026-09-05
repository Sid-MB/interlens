# `attach_advice`

Turn payload rows with each advised turn's trace row attached under `advice`.

```python
attach_advice(rows: Sequence[dict], turns: dict[str, dict]) -> list[dict]
```

Defined in [`interlens.arena.viz.advice`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/advice.py#L125-L132)

Keyed on the turn's own `idx`, which is the index the sidecar recorded and the id the transcript, the
scrubber and every jump link already agree on.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rows` | `Sequence[dict]` | *required* |  |
| `turns` | `dict[str, dict]` | *required* |  |
