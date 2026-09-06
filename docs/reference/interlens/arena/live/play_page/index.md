# `play_page`

Module `interlens.arena.live.play_page`

The live episode page: the visualizer's episode view, plus the controls to play in it.

This is deliberately the EXISTING episode page and not a new one. The body is assembled from the same fragments
the static page uses (`viz.page._chat_bubbles`/`_sidebar`/`_game_cards`/`_issue_pane`, `viz.chrome`'s
topbar and summary strip) inside the same `viz.page._document` shell, and the same chart/transcript/hover JS
runs on the same `PAYLOAD` object. What live play adds is a live UPDATE path (`assets/js_live.py`) and two
docks; everything a reader already knows how to read stays exactly where it was.

Rendering server-side from a snapshot, rather than booting an empty page that fetches, is what makes a reload
mid-episode land on the full transcript immediately and then attach to the stream — no flash of an empty game,
no divergence between what was rendered and what is being streamed.

The two docks:

- the HUMAN CONTROL DOCK — an offer builder generated from the deal space (one selector per issue, so an
  unrepresentable deal cannot be expressed), accept/reject/walk/pass buttons enabled from the server's own
  legality verdict, a public message box, a private scratchpad recorded as `TurnRecord.human_note`, and the
  seat's PRIVATE score sheet with its values and threshold. The player negotiates under exactly the information
  a model seat has, which is the only way a human turn is comparable to a model one.
- the SWAP DOCK — reassign any seat mid-game.

Everything on both docks that the moment decides — which offers may be accepted, which buttons are legal, what
the package under construction is worth — is filled by the browser from the `awaiting_human` event. What the
GAME decides — the issues, the options, the sheet — is rendered here, once, so the page does not rearrange
itself when a turn becomes the player's.

Owned by lane D.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `SEAT_KIND_LABELS` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`render_live_html`](render_live_html.md) | The complete live page for a session. |
