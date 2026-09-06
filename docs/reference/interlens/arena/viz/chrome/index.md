# `chrome`

Module `interlens.arena.viz.chrome`

The shell every page wears, and the wire form of the payload it carries.

Two things live here because both are shared by all three page kinds and neither belongs to any one of them.

**The chrome** — the sticky top bar (run identity, episode navigation, the quick read, theme and help buttons)
and the keyboard-help overlay. Navigation is rendered as plain links and a `<select>`, so it works with
scripting off; the browser layer only adds the shortcuts.

Where the navigation goes is marked with :data:`NAV_MARKER` rather than filled in at render time. A page cannot
know its own siblings — `render_episode_html` is handed one payload — while the exporter, which writes the whole
run, knows all of them but only after the last page is rendered. So the exporter writes the pages and then
replaces one comment in each. A page rendered on its own keeps the comment, which is invisible.

**The wire payload** — :func:`slim_payload` replaces every turn's inlined prompt view with indices into one
de-duplicated message pool. A six-seat thirty-turn episode repeats its system prompt on every turn and re-states
the whole history in each view, so the same bytes were being shipped dozens of times: on a representative
30-turn page the pool takes the embedded data from 566 KB to 332 KB with nothing removed. The returned dict is a
render-time copy — :meth:`RunDir.payload`'s own return value is untouched, because it is a public API whose
consumers expect real message dicts.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `NAV_MARKER` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`distance_to_nbs`](distance_to_nbs.md) | How far the deal that closed sits from the Nash bargaining solution, in the chart's own plane. |
| [`help_overlay`](help_overlay.md) | The keyboard-help overlay. |
| [`inject_nav`](inject_nav.md) | Put a page's navigation into its top bar. |
| [`nav_group`](nav_group.md) | The prev/next links and episode picker for the page at `position` in `rows`. |
| [`quick_stats`](quick_stats.md) | The two-or-three-number read that rides in the top bar and stays visible while scrolling. |
| [`slim_payload`](slim_payload.md) | A copy of `payload` whose per-turn prompt views are indices into a shared `msgpool`. |
| [`stat`](stat.md) | One cell of the summary strip: a small caption, the number, and a line of context under it. |
| [`summary_strip`](summary_strip.md) | The whole episode in one row: did it close, how good was it, how far from the normative anchor, who was left below their threshold, how much of it the engine fabricated, how long it ran, what it cost. |
| [`topbar`](topbar.md) | The sticky top bar: run identity on the left, the navigation slot, the quick read, theme and help. |
| [`unslim_payload`](unslim_payload.md) | The inverse of :func:`slim_payload`: pooled view indices back to full `{role, content}` messages. |
