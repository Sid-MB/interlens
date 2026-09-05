# `interlens.arena.viz.assets.js_episode`

The episode page's own wiring: build the marks, render the panels, and keep chart and transcript in sync.

The sync is two-way and goes through one function on each side. Clicking a numbered move on the frontier selects
that turn in the transcript and scrolls to it; selecting a turn — by click, by scrubber chip, by regret bar, or
with `j`/`k` — rings the deal that turn put on the chart. Before this, the chart could reach the transcript
but the transcript could not reach the chart, so a reader following the text had to hunt for the corresponding
point by eye.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_EPISODE` |  |  |
