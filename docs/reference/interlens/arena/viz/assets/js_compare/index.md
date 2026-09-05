# `interlens.arena.viz.assets.js_compare`

The comparison page's wiring: one shared frontier carrying both trajectories, and two synchronized columns.

The two columns render with DIFFERENT element-id prefixes (`lturn-` / `rturn-`). They have to: both sides
number their turns from zero, so a single prefix put two elements with the same id on one page and every lookup
silently resolved to whichever came first.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_COMPARE` |  |  |
