# `interlens.arena.live.lobby_page`

The lobby: choose a game and decide who plays each seat.

Built on `viz.page._document`, the same shell the episode pages use, so the lobby inherits the visualizer's
CSS, its light/dark handling and its layout without a second stylesheet to keep in step. Pure string-building
like the rest of the visualizer: this module renders, it never fetches or mutates.

The one thing the lobby must get right is not offering a configuration that will fail. Model capabilities differ
in ways that are hard errors rather than degradations — the Claude-5 models reject a temperature outright, Fable
cannot turn thinking off, Haiku refuses adaptive thinking — so the seat cards are generated FROM each model's
declared `thinking_modes` and `supports_temperature` rather than from a fixed set of controls. A budget cap
is required before any metered seat can start, for the same reason: it is the only thing standing between a
click and an unbounded bill.

A seat nobody has configured opens on the provider's own defaults — the model it flagged
(:func:`~interlens.arena.live.provider.default_model_id`) with thinking on wherever that model allows it
(:func:`~interlens.arena.live.provider.default_thinking`) — and the "all model seats" row
(:func:`_all_seats_row`) sets a whole lineup at once. No model id is spelled anywhere in this module. The
:func:`_shuffle_bar` button randomizes who plays which party — seat position is not neutral, since the proposer
order rotates from the proposer base — and shows the permutation the server applied.

**Every control is rendered here, in Python, exactly once.** The browser layer changes the VALUES of controls
that already exist and rebuilds only option lists (the thinking modes a newly picked model allows, the instances
a newly picked bank contains); it never builds a seat card. When an edit changes the shape of the page — a bank
with a different party count, so a different number of seat cards — the browser reloads and this function
renders it again. A second copy of the card markup in JavaScript would be the obvious way to do it and the fast
way to end up with two lobbies that disagree about what a seat is.

Owned by lane C.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `CSS_LOBBY` |  |  |
| `LOBBY_RULES` |  |  |
| `NO_INSTRUCTION_KINDS` |  |  |
| `SEAT_KIND_LABELS` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`render_lobby_html`](render_lobby_html.md) | The complete lobby page. |
