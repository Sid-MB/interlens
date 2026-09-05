# `insert_needle`

Paragraph-boundary insertion at a seeded uniform depth.

```python
insert_needle(rng: random.Random, hay: str, needle: str) -> tuple[str, float]
```

Defined in [`interlens.arena.scenarios.dlc.build`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/build.py#L149-L157)

Returns `(text, depth_fraction)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rng` | `random.Random` | *required* |  |
| `hay` | `str` | *required* |  |
| `needle` | `str` | *required* |  |
