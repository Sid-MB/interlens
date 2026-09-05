# `export_episode`

Write one episode's page into `out_dir` as `<episode_id>.html` and return its path.

```python
export_episode(
	run: str | Path,
	episode_path: str | Path,
	out_dir: str | Path,
	*,
	reconstruct: bool = True,
	annotations_dirname: str = 'annotations',
) -> Path
```

Defined in [`interlens.arena.viz.export`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/export.py#L191-L201)

`annotations_dirname` selects the per-run annotation subdirectory (see
:class:`~interlens.arena.viz.episode.RunDir`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `run` | `str \| Path` | *required* |  |
| `episode_path` | `str \| Path` | *required* |  |
| `out_dir` | `str \| Path` | *required* |  |
| `reconstruct` | `bool` | `True` |  |
| `annotations_dirname` | `str` | `'annotations'` |  |
