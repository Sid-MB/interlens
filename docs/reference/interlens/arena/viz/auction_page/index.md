# `auction_page`

Module `interlens.arena.viz.auction_page`

The auction episode page's own panels — the four charts design.md §10 commits to, plus the per-turn
counterfactual table.

Split out of :mod:`~interlens.arena.viz.page` rather than branched inside it, because none of these panels
share a line with the negotiation ones: an auction has no deal space to embed, so there is no frontier chart,
no solution-concept legend, and no regret strip. What IS shared comes back in through `page.py` — the shell,
the transcript, the census and vintage badges, the prompt audit, and the chat bubbles — so this module renders
only what is genuinely new.

Everything here is server-rendered SVG and HTML. The browser layer
(:data:`~interlens.arena.viz.assets.js_auction.JS_AUCTION`) adds the stage scrubber, the hover cards, and the
transcript cross-links; with scripting off, every number and every mark is still in the document, which is the
same contract the rest of the visualizer keeps.

The four panels, in the order the page carries them:

1. :func:`bid_ladder` — price against round, stages laid out left to right on one shared price scale, one line
   per seat, exits and standing-high transitions marked, private valuations as per-stage reference ticks, with
   the collusion-onset stage and every detected defection shaded onto the stage axis.
2. :func:`allocation_strip` — one bar per lot per stage, private valuations as ticks, the clearing price as the
   tau-line. A direct adaptation of `page._issue_bars_svg`'s scale-and-tick construction.
3. :func:`settlement_panel` — winner, payment and surplus per stage, with the episode total.
4. :func:`dm_graph` — the directed message graph with a stage scrubber and the per-dyad counts beside it.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `GRAPH` |  |  |
| `LADDER` |  |  |
| `STRIP` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`allocation_strip`](allocation_strip.md) | One bar per lot per stage: every seat's private valuation as a tick, the clearing price as the tau-line. |
| [`auction_body`](auction_body.md) | The auction episode page's four panels plus the counterfactual table, in reading order. |
| [`auction_info_panel`](auction_info_panel.md) | The auction page's reading guide — what every measure on the page means and what it does not. |
| [`auction_setup_panel`](auction_setup_panel.md) | The side panel: the mechanism, the five public cards, the lot catalogue, and every stage's frozen draw. |
| [`auction_summary_strip`](auction_summary_strip.md) | The whole auction episode in one row: the format, how efficient it was, what it raised against benchmark, whether anything was suppressed, and how much of it was model behaviour at all. |
| [`bid_ladder`](bid_ladder.md) | Price against bidding round, every stage of the episode side by side on one shared price scale. |
| [`counterfactual_table`](counterfactual_table.md) | Every committed turn beside what the two computable rules would have played there. |
| [`dm_graph`](dm_graph.md) | The directed message graph over the seats, with a stage scrubber and the per-dyad counts beside it. |
| [`settlement_panel`](settlement_panel.md) | Winner, payment and surplus per stage, with the episode total — what replaces `chrome.summary_strip`'s negotiation field list. |
