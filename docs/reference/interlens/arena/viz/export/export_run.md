# `export_run`

Render every episode of a run to its own page in `out_dir`, plus an `index.html` listing them with the numbers that say which are worth opening.

```python
export_run(
	run: str | Path,
	out_dir: str | Path,
	*,
	limit: int | None = None,
	episode_ids: Sequence[str] | None = None,
	reconstruct: bool = True,
	annotations_dirname: str = 'annotations',
) -> dict
```

Defined in [`interlens.arena.viz.export`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/export.py#L204-L275)

Returns a manifest (also written as `manifest.json`).

`limit` renders only the first `limit` episodes in sorted path order — the fast path for a spot check on a
campaign cell with hundreds of episodes. `annotations_dirname` selects which per-run annotation subdirectory
the post-hoc oracles are read from (default `"annotations"`; e.g. `"annotations_v1"` for a re-annotated
set — see :class:`~interlens.arena.viz.episode.RunDir`).

`episode_ids` publishes a CHOSEN subset instead, in the order given. A campaign cell of a hundred-plus
Opus episodes is tens of megabytes of pages, so a published hub is routinely a representative selection
rather than the whole cell — and a selection made by a caller's own rule (spanning outcomes, seats, or a
behaviour of interest) is worth far more than the first N in path order. The chosen ids are recorded in the
manifest as `selection`, so a hub can state which episodes it published and which it did not; an id the run
does not hold is reported in `failures` rather than silently skipped. `limit` still applies afterwards.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `run` | `str \| Path` | *required* |  |
| `out_dir` | `str \| Path` | *required* |  |
| `limit` | `int \| None` | `None` |  |
| `episode_ids` | `Sequence[str] \| None` | `None` |  |
| `reconstruct` | `bool` | `True` |  |
| `annotations_dirname` | `str` | `'annotations'` |  |
