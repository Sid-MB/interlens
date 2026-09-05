# `render_compare`

The interactive HTML for the `index`-th matched pair between two runs, as a string.

```python
render_compare(
	left_run: str | Path,
	right_run: str | Path,
	*,
	index: int = 0,
	pair_fields: tuple[str, ...] = DEFAULT_PAIR_KEY,
	reconstruct: bool = True,
	annotations_dirname: str = 'annotations',
) -> str
```

Defined in [`interlens.arena.viz.export`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/export.py#L179-L188)

`annotations_dirname` selects the per-run annotation subdirectory both sides are read with.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `left_run` | `str \| Path` | *required* |  |
| `right_run` | `str \| Path` | *required* |  |
| `index` | `int` | `0` |  |
| `pair_fields` | `tuple[str, ...]` | `DEFAULT_PAIR_KEY` |  |
| `reconstruct` | `bool` | `True` |  |
| `annotations_dirname` | `str` | `'annotations'` |  |
