# `interlens.arena.live.assets.js_live`

The live page's browser layer: subscribe, merge, redraw, and take the player's move.

The merge rule is one line and worth stating exactly, because everything else follows from it: a
`turn_appended` event's `turn` is PUSHED onto `PAYLOAD.turns` — the array is mutated in place, never
replaced — and then the existing draw functions are called again. The episode page already re-renders entirely
from the in-memory `PAYLOAD` (that is how its seat and oracle selectors work), so a live page is that same page
with a growing array. Nothing about the chart, the regret bars, the hover cards or the transcript cards is
reimplemented here.

Per turn: push the row, insert the server-rendered `bubble_html` into the chat pane, `drawChart()` and
`drawRegret()`, wire the ONE new turn card, and re-mount the sidebar (it snapshots turns at mount, and a
re-mount is cheap enough to be the honest fix).

Reconnects are handled by `EventSource`, which resends `Last-Event-ID` by itself; the session replays its log
from there, so a dropped connection costs nothing. A page that has been away long enough to be unsure re-fetches
`/state` instead of trusting an incremental merge.

**The one merge case an append cannot express.** Three fields on a payload row — `published`, `offer_id` and
`standing_deal_index` — are properties of a turn's POSITION IN THE SEQUENCE, and a retried turn retroactively
flips an EARLIER row's `published` to `False` (`viz.episode.public_ledger`, and see `live.payload
.turn_delta`, which re-derives the ledger over the whole accumulated list on the server). The
`turn_appended` event carries the new row only, so corrections to earlier rows do not ride along. The client
therefore detects the one situation that produces them — an arriving turn occupying a (round, phase, seat) slot
some earlier row already holds, which is what a retry is — and reloads the page, which re-renders server-side
from `/state` and is correct by construction. Reloading rather than patching is deliberate: the chat bubbles
are server-rendered, so there is no client-side renderer to rebuild a corrected transcript with, and inventing
one is exactly the second bubble renderer this design exists to avoid. Retries are rare (one per seat, round and
phase at most) and the reload is rate-limited so a pathological run cannot spin.

**Why the episode wiring is here rather than imported.** `viz.assets.js_episode` wires the static page's draw
functions but does its per-card binding inside `drawTurns`, where a live page cannot reach it to wire ONE
arriving card. The wiring below is that module's, restructured around :js:func:`wireTurnCard` so a full draw and
a single append share it. Everything it draws with — `frontierChart`, `turnCard`, `mountSidebar`,
`regretChart`, the hover and counterfactual cards — is imported unchanged from `viz.assets`.

Owned by lane D.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_LIVE` |  |  |
