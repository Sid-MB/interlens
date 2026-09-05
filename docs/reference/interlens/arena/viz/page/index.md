# `interlens.arena.viz.page`

HTML assembly: a payload in, one self-contained interactive page out.

Everything that can be rendered without JavaScript is rendered here in Python — the summary strip, the game side
panel, every score sheet, the numeric table view of the chart, the pairing banner, the comparison score table and
its verdict, and the whole run index including its rows. The browser script only draws the two charts and the
transcript cards. That split is deliberate: the numbers are the deliverable, so they must be in the document even
if the script never runs, and it makes the tests able to assert on real structure and real values without a
browser.

Pages are opened over `file://`, so nothing is fetched: the stylesheet and script are inlined, and the payload
travels in a `<script type="application/json">` tag (data in a data position — never interpolated into
executable code, and closing-tag sequences are escaped).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `AUCTION_INDEX_COLUMNS` |  |  |
| `INDEX_COLUMNS` |  |  |
| `SIDEBAR_TABS` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`occupant_defaults`](occupant_defaults.md) | Each seat's DEFAULT occupant: the one it played its first recorded turn under. |
| [`preference_visibility`](preference_visibility.md) | The compact index label for a negotiation's information condition. |
| [`render_auction_episode_html`](render_auction_episode_html.md) | One self-contained interactive page for one auction episode. |
| [`render_compare_html`](render_compare_html.md) | One self-contained page for a seat-swap comparison: a verdict strip, the quantified score table with paired deltas, one shared frontier carrying both trajectories, and two synchronized transcript columns with the divergence point marked. |
| [`render_episode_html`](render_episode_html.md) | One self-contained interactive page for one episode. |
| [`render_index_html`](render_index_html.md) | A run index: one row per generated page, sortable on every column and filterable by text, outcome, and whether the engine fabricated any turns. |
