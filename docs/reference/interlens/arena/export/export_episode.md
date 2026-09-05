# `export_episode`

Write `<id>.md` and `<id>.html` for one episode into `out_dir`; returns their paths.

```python
export_episode(episode: dict, instance: dict | None, out_dir: str | Path) -> dict
```

Defined in [`interlens.arena.export`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/export.py#L259-L267)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `instance` | `dict \| None` | *required* |  |
| `out_dir` | `str \| Path` | *required* |  |
