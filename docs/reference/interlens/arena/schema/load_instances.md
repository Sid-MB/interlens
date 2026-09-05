# `load_instances`

Load an instance pool saved by `save_instances` (or by the arena experiments — the pre-rename `env` key is migrated on read).

```python
load_instances(
	root: str | Path,
	scenario: str,
	level: int | None = None,
	name: str | None = None,
) -> list[Instance]
```

Defined in [`interlens.arena.schema`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L340-L346)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `root` | `str \| Path` | *required* |  |
| `scenario` | `str` | *required* |  |
| `level` | `int \| None` | `None` |  |
| `name` | `str \| None` | `None` |  |
