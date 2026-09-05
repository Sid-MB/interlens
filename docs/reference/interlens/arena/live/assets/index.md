# `interlens.arena.live.assets`

The live pages' browser layer, as Python strings — same convention as `viz.assets`.

Only the LIVE parts live here. The chart, hover cards, transcript cards, sidebar and page shell are imported from
`viz.assets` unchanged: a live page is the episode page plus an update path, and reimplementing any of the
visualizer in a second copy is how the two would start disagreeing about what the same episode looks like.

No external assets, no build step, no CDN — the pages must work on a cluster node behind a firewall.

## Modules

- [`js_live`](js_live/index.md) — The live page's browser layer: subscribe, merge, redraw, and take the player's move.
- [`js_lobby`](js_lobby/index.md) — The lobby's browser layer: edit the seat lineup, then start the game.

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`JS_LIVE`](js_live/index.md#attributes) | `interlens.arena.live.assets.js_live` |  |
| [`JS_LOBBY`](js_lobby/index.md#attributes) | `interlens.arena.live.assets.js_lobby` |  |
