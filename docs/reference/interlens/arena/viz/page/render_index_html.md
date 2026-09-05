# `render_index_html`

A run index: one row per generated page, sortable on every column and filterable by text, outcome, and whether the engine fabricated any turns.

```python
render_index_html(
	rows: list[dict],
	title: str,
	note: str = '',
	readme_markdown: str = '',
	columns: list[tuple] | None = None,
) -> str
```

Defined in [`interlens.arena.viz.page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/page.py#L1074-L1120)

Sorting and filtering are client-side over the rows already in the document — there is no second copy of the
data in a JSON blob, so a 200-episode index stays a small file and still reads correctly with scripting off.
The row count of what survives a filter is always on screen, because a filter that silently hides rows is how
a reader concludes a run has fewer episodes than it has.

`columns` selects the column set, defaulting to :data:`INDEX_COLUMNS` (the negotiation one). Pass
:data:`AUCTION_INDEX_COLUMNS` for an auction run, whose rows carry a different measure set entirely — the
scale for the `bar` columns is taken from whichever key the first `bar` column names, so a caller does
not have to supply it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rows` | `list[dict]` | *required* |  |
| `title` | `str` | *required* |  |
| `note` | `str` | `''` |  |
| `readme_markdown` | `str` | `''` |  |
| `columns` | `list[tuple] \| None` | `None` |  |
