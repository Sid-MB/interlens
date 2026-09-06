# `payload`

Module `interlens.arena.live.payload`

Per-turn slices of the visualizer payload, for streaming one turn at a time.

A live page and a static page must show the same thing, and the only way to be sure of that is for both to come
out of the same code. So there is no live payload builder: :func:`turn_delta` calls the visualizer's own
`viz.episode._turn_payload` and :func:`bubble_html` its own `viz.page._chat_bubble`, which are exactly the
per-turn units `episode_payload` and `_chat_bubbles` are built from. A streamed turn is therefore
byte-identical to the row a reload rebuilds, and a drift between the two is not a bug that can happen — it would
require the shared function to disagree with itself.

Everything episode-scoped (the geometry, the seat kinds, the seat->party map) is computed ONCE per session and
passed in, because rebuilding a game's geometry on every turn is the one thing here expensive enough to notice.

Owned by lane B.

## Functions

| Name | Summary |
|---|---|
| [`bubble_html`](bubble_html.md) | The chat bubble for one turn, server-rendered by the visualizer's own `_chat_bubble`. |
| [`turn_delta`](turn_delta.md) | Append one committed turn's payload row to `rows` and return it — what a `turn_appended` event carries. |
