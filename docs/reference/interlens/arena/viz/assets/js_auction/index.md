# `interlens.arena.viz.assets.js_auction`

The auction episode page's wiring: the DM stage scrubber, the hover card on the bid ladder, and the
cross-links between every mark and the turn it belongs to.

Deliberately thin. Every panel on an auction page is rendered server-side in
:mod:`~interlens.arena.viz.auction_page`, including all of its SVG and all of its numbers, so this layer only
adds behaviour that needs a pointer: with scripting off the page loses the stage filter and the rich hover, and
keeps every mark, every `<title>` tooltip and every table cell.

It shares the transcript layer with the negotiation page (`turnCard` renders an auction turn without a game
geometry, which is the graceful-degradation path that already existed), and it does not touch the frontier
chart or the regret strip, neither of which an auction has.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_AUCTION` |  |  |
