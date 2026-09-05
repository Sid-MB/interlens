# `check_reasoning_leak`

Scan a played episode for reasoning leakage: any turn whose raw completion contains a `<think>` block whose content then appears verbatim in a LATER turn's visible content (meaning another seat saw it).

```python
check_reasoning_leak(episode: Episode | dict, *, fragment_length: int = 80) -> dict
```

Defined in [`interlens.arena.gates`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/gates.py#L67-L92)

Accepts a live `Episode` or its stored JSON dict.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | [Episode](../schema/Episode.md) \| dict | *required* |  |
| `fragment_length` | `int` | `80` |  |
