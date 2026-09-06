# `live`

Package `interlens.arena.live`

Live play: watch an arena episode as it happens, reconfigure its seats, and play one yourself.

The rest of the arena is run-then-inspect — episodes roll out headlessly and the visualizer renders the JSON
afterwards. This package adds the interactive half: a localhost server that streams a negotiation turn by turn
into the visualizer's own episode page, lets every seat be configured (and re-configured mid-game) between a
model, a computable policy, an omniscient oracle and a person, and blocks a human seat on a browser form that
produces a move byte-identical in form to a model's.

Three design commitments hold the whole thing together:

1. **One payload code path.** A streamed turn and a reloaded page come out of the same visualizer functions
   (`viz.episode._turn_payload`, `viz.page._chat_bubble`), so live and static views cannot drift.
2. **The stream follows the disk.** Turns are broadcast from an engine observer that runs after the episode is
   persisted, so nothing is ever shown that a reload would not find.
3. **The library stays generic.** Instance banks, framings, scaffolds and model credentials enter through a
   :class:`ScenarioProvider` the experiment implements; interlens never learns what a framing is.

Usage:

```python
from interlens.arena.live import run_live_server
run_live_server(MyProvider(), port=8080, run_dir="results/live")
```

Stdlib only (`http.server` + server-sent events), like the rest of the visualizer.

## Modules

- [`assets`](assets/index.md) — The live pages' browser layer, as Python strings — same convention as `viz.assets`.
- [`events`](events/index.md) — The live-play wire protocol: every server-sent event a session can emit, in one place.
- [`human`](human/index.md) — `HumanParticipant`: a seat played by a person in a browser.
- [`lobby_page`](lobby_page/index.md) — The lobby: choose a game and decide who plays each seat.
- [`payload`](payload/index.md) — Per-turn slices of the visualizer payload, for streaming one turn at a time.
- [`play_page`](play_page/index.md) — The live episode page: the visualizer's episode view, plus the controls to play in it.
- [`provider`](provider/index.md) — The seam between the live server and whatever experiment supplies its games.
- [`router`](router/index.md) — `LiveSeatRouter`: a seat table whose occupants can change while the episode is running.
- [`server`](server/index.md) — The HTTP surface: a stdlib `ThreadingHTTPServer` serving the lobby, the live page, and the event stream.
- [`session`](session/index.md) — `LiveSession`: one live game — the engine thread, the event log, and everything the browser can do to it.
- [`style`](style/index.md) — The rules the lobby and the play page both need: form controls, seat cards, and the two docks.

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`BankInfo`](provider/BankInfo.md) | `interlens.arena.live.provider` | One instance bank the lobby may draw a game from. |
| [`HumanParticipant`](human/HumanParticipant.md) | `interlens.arena.live.human` | A negotiation seat whose moves come from a browser. |
| [`LiveSeatRouter`](router/LiveSeatRouter.md) | `interlens.arena.live.router` | A :class:`~interlens.arena.table.SeatRouter` that supports mid-episode occupant changes. |
| [`LiveSession`](session/LiveSession.md) | `interlens.arena.live.session` | One live episode plus its subscribers. |
| [`ModelInfo`](provider/ModelInfo.md) | `interlens.arena.live.provider` | One model the lobby may offer for an `llm` seat. |
| [`PendingRequest`](human/PendingRequest.md) | `interlens.arena.live.human` | One open ask of a human seat — what the browser renders a form from, and what the server validates a submission against. |
| [`PreparedGame`](provider/PreparedGame.md) | `interlens.arena.live.provider` | One playable game, fully assembled — the provider's answer to a lobby configuration. |
| [`SEAT_KINDS`](provider/index.md#attributes) | `interlens.arena.live.provider` |  |
| [`ScenarioProvider`](provider/ScenarioProvider.md) | `interlens.arena.live.provider` | What an experiment must supply for its games to be playable live. |
| [`SeatConfig`](provider/SeatConfig.md) | `interlens.arena.live.provider` | What the lobby says should sit in one seat — the unit of both initial configuration and a mid-game swap. |
| [`SessionManager`](session/SessionManager.md) | `interlens.arena.live.session` | The server's session registry. v1 holds ONE active session at a time. |
| [`make_live_server`](server/make_live_server.md) | `interlens.arena.live.server` | Bind (but do not run) the live-play server over `provider`. |
| [`run_live_server`](server/run_live_server.md) | `interlens.arena.live.server` | Serve live play until interrupted — bind, print the banner (including the `ssh -L` line, reusing `viz.serve.serve_banner`'s form), then block in `serve_forever`. |
