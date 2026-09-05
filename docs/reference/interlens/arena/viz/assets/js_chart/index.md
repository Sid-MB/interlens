# `interlens.arena.viz.assets.js_chart`

Browser layer, part 2: the two charts.

**The frontier chart** places every deal in the instance's deal space, draws the efficient envelope, the play
trajectory, and the reference marks, and lets a reader inspect any of the `|D|` deals — not only the marked
ones — by hovering: one handler on the SVG finds the nearest deal in plot coordinates rather than attaching
thousands of listeners. Hover opens the headline read in the side panel AND the rich hover card at the pointer
(`js_hover`: what the point is, the deal in named options, the reward stats, and the party ranking); a click
*pins* both. Every mark kind is covered by the same two calls, so a mark can never exist without a card.

It also zooms and pans, in plain SVG with no library: the view is the `viewBox`, so zooming is arithmetic on
four numbers and every mark stays vector-crisp. Wheel-zoom is deliberately gated behind Ctrl/⌘ or Shift — an
ungated wheel over a chart hijacks page scrolling, which is the single most irritating thing a chart can do — and
the explicit +/−/reset buttons carry the same behaviour for anyone who would rather click. Because the pointer
maths reads the *current* viewBox, nearest-deal hover keeps working at every zoom level.

**The regret strip** is one series (per-turn regret against the selected oracle), so it carries no legend: the
title names it. Non-zero bars are direct-labelled and every bar jumps to its turn.

Both return a small handle so the page can drive them from elsewhere — above all `focusTurn`, which is how
clicking a transcript turn lights up the deal it put on the table.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_CHART` |  |  |
