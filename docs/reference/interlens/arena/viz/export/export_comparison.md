# `export_comparison`

Pair two runs on `pair_fields` and write one comparison page per matched pair, plus an index and the pairing report.

```python
export_comparison(
	left_run: str | Path,
	right_run: str | Path,
	out_dir: str | Path,
	*,
	limit: int | None = None,
	pair_fields: tuple[str, ...] = DEFAULT_PAIR_KEY,
	reconstruct: bool = True,
	select: str = 'first',
	annotations_dirname: str = 'annotations',
) -> dict
```

Defined in [`interlens.arena.viz.export`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/export.py#L278-L341)

Returns a manifest (also written as `manifest.json`).

`select` (see :data:`~interlens.arena.viz.compare.SELECTIONS`) decides which pairs a `limit` keeps —
`"largest-effect"` or `"deal-flip"` rather than the arbitrary first few. `annotations_dirname` selects
which per-run annotation subdirectory BOTH sides read their post-hoc oracles from (default `"annotations"`;
e.g. `"annotations_v1"` — see :class:`~interlens.arena.viz.episode.RunDir`).

The pairing report is part of the deliverable, not a log line: it names how many episodes matched, which keys
went unmatched, and how the rendered pairs were selected, so a partially-complete campaign is visible as
partial rather than quietly rendering whichever cells happened to finish.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `left_run` | `str \| Path` | *required* |  |
| `right_run` | `str \| Path` | *required* |  |
| `out_dir` | `str \| Path` | *required* |  |
| `limit` | `int \| None` | `None` |  |
| `pair_fields` | `tuple[str, ...]` | `DEFAULT_PAIR_KEY` |  |
| `reconstruct` | `bool` | `True` |  |
| `select` | `str` | `'first'` |  |
| `annotations_dirname` | `str` | `'annotations'` |  |
