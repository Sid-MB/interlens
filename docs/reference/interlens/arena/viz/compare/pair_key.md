# `pair_key`

The pairing key of an episode: the tuple of its `fields`.

```python
pair_key(episode: dict, fields: tuple[str, ...] = DEFAULT_PAIR_KEY) -> tuple
```

Defined in [`interlens.arena.viz.compare`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/compare.py#L50-L53)

Two episodes with equal keys were played on the
identical instance, seed, protocol arm, and sweep cell, and so differ only in who sat where.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `fields` | `tuple[str, ...]` | `DEFAULT_PAIR_KEY` |  |
