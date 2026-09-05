# `interlens.arena.viz.assets.js_index`

The run index's browser layer: sort and filter, over the rows already in the document.

Deliberately **not** payload-driven. The rows are rendered server-side as a real table — every number visible with
scripting off — and sorting reads a `data-sort` attribute off each cell rather than a parallel JSON copy of the
same data. A hundred-episode index therefore costs one table, not a table plus its duplicate.

Filtering is a text match across the row plus two chips (deal / no deal, has fabricated turns), and the count of
what survives is always on screen, because a filter that silently hides rows is how a reader concludes a run has
fewer episodes than it does.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_INDEX` |  |  |
