# `interlens.arena.viz.assets`

The inline stylesheet and browser layer — no external assets of any kind.

Every generated page is opened straight off a filesystem path (`file://`), often on a cluster login node behind
no web server, so a single request to a CDN would leave the chart blank. The CSS and JS therefore live here as
Python strings that get inlined into the HTML.

The layer is assembled from small pieces rather than one string, because they have genuinely different jobs and
different pages want different subsets — the run index carries no episode payload, so it loads the utilities and
the shell and none of the data layer:

===================  =========================================================================================
module               what it holds
===================  =========================================================================================
`css`              the design system: tokens, light/dark, the action-type grammar, layout, controls
`js_core`          `JS_UTIL` (formatting + DOM helpers) and `JS_CORE` (payload, view rehydration, deals)
`js_hover`         the rich hover card every chart point carries, incl. the solution-concept explanations
`js_chart`         the frontier chart (hover, pin, zoom/pan) and the regret strip
`js_transcript`    turn cards, the scrubber, lazily-built prompt bodies, turn selection
`js_sidebar`       the tabbed sidebar and the IntersectionObserver scroll sync that drives it
`js_shell`         theme toggle, episode navigation, keyboard bindings, the help overlay
`js_episode`       the episode page's wiring
`js_auction`       the auction episode page's wiring (stage scrubber, ladder hover, transcript sync)
`js_compare`       the comparison page's wiring
`js_index`         the run index's sort and filter
===================  =========================================================================================

`JS` is the bundle every data page shares (utilities, data layer, charts, transcript, shell), so a page's own
script is only its wiring. `JS_INDEX_PAGE` is the index's smaller bundle.

**Colour.** Both modes are explicitly selected, not derived by flipping the light values, and the categorical
slots are capped at THREE. That cap is the binding constraint of the colour formula for a scatter: with all pairs
of series simultaneously on screen (which is what a scatter does, unlike a bar chart's adjacent pairs), only the
first three slots clear the colour-blindness and normal-vision separation floors in both modes. The three slots
carry the only three identities that must be told apart by colour:

============  =========================  ==========================
slot          episode page               comparison page
============  =========================  ==========================
1 (blue)      what the model actually did the left episode
2 (orange)    what the oracle recommends  the right episode
3 (aqua)      normative solution points   normative solution points
============  =========================  ==========================

Everything else is encoded by **shape plus a direct label**: NBS, KS, and EGAL are aqua stars; UTIL and MNW are
violet triangles; every concept is directly labelled on the chart. Violet is a redundant reference-point accent,
not a fourth trajectory identity—the triangle and labels carry the distinction without colour. The per-party
ideal points share one aqua diamond with the party named on hover and enumerated in the side panel's table. Deals themselves are chart chrome,
not a series: dominated deals are muted dots, frontier deals carry the secondary-ink ring. Slot 3 sits below 3:1
against the light surface, which obligates the relief rule — hence the always-visible direct labels and the
numeric table view that every chart ships with. Action types on the transcript are STATES rather than a series, so
they wear the reserved status palette and always carry a glyph and a word beside the colour.

## Modules

- [`css`](css/index.md) — The one stylesheet every page wears — a small design system, inlined.
- [`js_auction`](js_auction/index.md) — The auction episode page's wiring: the DM stage scrubber, the hover card on the bid ladder, and the cross-links between every mark and the turn it belongs to.
- [`js_chart`](js_chart/index.md) — Browser layer, part 2: the two charts.
- [`js_compare`](js_compare/index.md) — The comparison page's wiring: one shared frontier carrying both trajectories, and two synchronized columns.
- [`js_core`](js_core/index.md) — Browser layer, part 1: the payload, the formatting helpers, and the deal-detail panel.
- [`js_episode`](js_episode/index.md) — The episode page's own wiring: build the marks, render the panels, and keep chart and transcript in sync.
- [`js_hover`](js_hover/index.md) — Browser layer, part 2a: the rich hover card that EVERY point on the frontier chart carries.
- [`js_index`](js_index/index.md) — The run index's browser layer: sort and filter, over the rows already in the document.
- [`js_shell`](js_shell/index.md) — Browser layer, part 4: the page shell — theme toggle, episode navigation, keyboard shortcuts, help overlay.
- [`js_sidebar`](js_sidebar/index.md) — Browser layer, part 5: the tabbed sidebar and the scroll sync that drives it.
- [`js_transcript`](js_transcript/index.md) — Browser layer, part 3: the transcript — turn cards, the scrubber, and lazy prompt bodies.

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`CSS`](css/index.md#attributes) | `interlens.arena.viz.assets.css` |  |
| [`JS_AUCTION`](js_auction/index.md#attributes) | `interlens.arena.viz.assets.js_auction` |  |
| [`JS_CHART`](js_chart/index.md#attributes) | `interlens.arena.viz.assets.js_chart` |  |
| [`JS_COMPARE`](js_compare/index.md#attributes) | `interlens.arena.viz.assets.js_compare` |  |
| [`JS_CORE`](js_core/index.md#attributes) | `interlens.arena.viz.assets.js_core` |  |
| [`JS_EPISODE`](js_episode/index.md#attributes) | `interlens.arena.viz.assets.js_episode` |  |
| [`JS_HOVER`](js_hover/index.md#attributes) | `interlens.arena.viz.assets.js_hover` |  |
| [`JS_INDEX`](js_index/index.md#attributes) | `interlens.arena.viz.assets.js_index` |  |
| [`JS_SHELL`](js_shell/index.md#attributes) | `interlens.arena.viz.assets.js_shell` |  |
| [`JS_SIDEBAR`](js_sidebar/index.md#attributes) | `interlens.arena.viz.assets.js_sidebar` |  |
| [`JS_TRANSCRIPT`](js_transcript/index.md#attributes) | `interlens.arena.viz.assets.js_transcript` |  |
| [`JS_UTIL`](js_core/index.md#attributes) | `interlens.arena.viz.assets.js_core` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS` |  |  |
| `JS_INDEX_PAGE` |  |  |
