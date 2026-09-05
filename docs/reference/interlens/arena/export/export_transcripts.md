# `export_transcripts`

Alias of :func:`export_run` with a caller-friendly signature (`episodes_dir, out_dir, instances_dir=`).

```python
export_transcripts(
	episodes_dir: str | Path,
	out_dir: str | Path,
	*,
	instances_dir: str | Path | None = None,
	annotations_dir: str | Path | None = None,
) -> dict
```

Defined in [`interlens.arena.export`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/export.py#L323-L328)

`annotations_dir` is accepted for interface stability but IGNORED — per-oracle regret is read from each
episode's own inline `round_checkpoints`, so no separate annotation store is needed.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episodes_dir` | `str \| Path` | *required* |  |
| `out_dir` | `str \| Path` | *required* |  |
| `instances_dir` | `str \| Path \| None` | `None` |  |
| `annotations_dir` | `str \| Path \| None` | `None` |  |
