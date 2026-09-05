# `save_instances`

Persist an instance pool as one JSON file (`{scenario}_L{level}.json` unless `name` overrides).

```python
save_instances(
	instances: list[Instance],
	root: str | Path,
	name: str | None = None,
) -> Path
```

Defined in [`interlens.arena.schema`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L330-L337)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instances` | list[[Instance](Instance.md)] | *required* |  |
| `root` | `str \| Path` | *required* |  |
| `name` | `str \| None` | `None` |  |
