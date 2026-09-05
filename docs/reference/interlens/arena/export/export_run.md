# `export_run`

Render every episode under `episodes_path` to `out_dir` (md + html each) plus an `index.html` / `index.md` linking them with one-line summaries.

```python
export_run(
	episodes_path: str | Path,
	instances_path: str | Path | None,
	out_dir: str | Path,
) -> dict
```

Defined in [`interlens.arena.export`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/export.py#L292-L320)

Returns a small manifest.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episodes_path` | `str \| Path` | *required* |  |
| `instances_path` | `str \| Path \| None` | *required* |  |
| `out_dir` | `str \| Path` | *required* |  |
