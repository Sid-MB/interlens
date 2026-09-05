# `pair_runs`

Pair every episode of one run against its key-matched counterpart in another, and build a comparison payload for each.

```python
pair_runs(
	left_run: str | Path,
	right_run: str | Path,
	*,
	pair_fields: tuple[str, ...] = DEFAULT_PAIR_KEY,
	limit: int | None = None,
	reconstruct: bool = True,
	select: str = 'first',
	annotations_dirname: str = 'annotations',
) -> tuple[list[dict], dict]
```

Defined in [`interlens.arena.viz.compare`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/compare.py#L240-L289)

Returns `(comparisons, report)`. The report counts matched pairs and lists unmatched keys on each side, so a
partially-complete campaign is visible as such. Where a key matches several episodes on a side (repeated
seeds), they are zipped in sorted episode-id order and the multiplicity is recorded.

`select` (one of :data:`SELECTIONS`) decides which pairs `limit` keeps. Ranking reads only each episode's
stored `outcome`, so choosing among hundreds of pairs costs nothing — the expensive payload build happens
only for the pairs that survive the limit. The report records the selection, because "the 6 largest movers" and
"6 arbitrary pairs" support very different readings of the same page count.

`annotations_dirname` selects the per-run annotation subdirectory BOTH runs read their post-hoc oracles from
(default `"annotations"`; e.g. `"annotations_v1"` — see :class:`~interlens.arena.viz.episode.RunDir`).

Both runs' geometry caches are per-`RunDir`; the LEFT run's geometry is used for both sides of a pair so the
frontier is built once and the two trajectories are provably drawn against the same numbers.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `left_run` | `str \| Path` | *required* |  |
| `right_run` | `str \| Path` | *required* |  |
| `pair_fields` | `tuple[str, ...]` | `DEFAULT_PAIR_KEY` |  |
| `limit` | `int \| None` | `None` |  |
| `reconstruct` | `bool` | `True` |  |
| `select` | `str` | `'first'` |  |
| `annotations_dirname` | `str` | `'annotations'` |  |
