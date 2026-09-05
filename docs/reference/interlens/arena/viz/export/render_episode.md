# `render_episode`

The interactive HTML for one episode of a run, as a string.

```python
render_episode(
	run: str | Path,
	episode_path: str | Path,
	*,
	reconstruct: bool = True,
	annotations_dirname: str = 'annotations',
) -> str
```

Defined in [`interlens.arena.viz.export`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/export.py#L171-L176)

`annotations_dirname` selects the per-run
annotation subdirectory (see :class:`~interlens.arena.viz.episode.RunDir`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `run` | `str \| Path` | *required* |  |
| `episode_path` | `str \| Path` | *required* |  |
| `reconstruct` | `bool` | `True` |  |
| `annotations_dirname` | `str` | `'annotations'` |  |
