# `server`

Module `interlens.arena.live.server`

The HTTP surface: a stdlib `ThreadingHTTPServer` serving the lobby, the live page, and the event stream.

Stdlib only, matching `viz/serve.py` — the visualizer's whole point is that it adds no dependency to a package
that is otherwise pure string-building, and a live server is not a good enough reason to put a web framework in
it. `ThreadingHTTPServer` gives a thread per request, which is what an SSE endpoint needs: those handlers are
long-lived, looping on their subscriber queue for the length of the game, and would block every other request on
a single-threaded server.

Routes (all JSON in, JSON out, except the two HTML pages):

===================================== ====== ==========================================================
Route                                 Method Purpose
===================================== ====== ==========================================================
`/`                                 GET    The lobby page (HTML)
`/play`                             GET    The live episode page (HTML), rendered from the snapshot
`/api/lobby`                        GET    Current lobby configuration + provider listings
`/api/lobby`                        POST   Partial lobby edit; returns the updated state
`/api/start`                        POST   Prepare a game and start a session -> `{sid, episode_id}`
`/api/session/{sid}/state`          GET    Full snapshot: payload, phase, awaiting, occupants, seq
`/api/session/{sid}/events`         GET    The SSE stream (honours `Last-Event-ID`)
`/api/session/{sid}/act`            POST   A human seat's move
`/api/session/{sid}/swap`           POST   Replace a seat's occupant
`/api/session/{sid}/stop`           POST   End the session
`/api/reset`                        POST   Drop the session and return to the lobby
===================================== ====== ==========================================================

The server binds but does not start, exactly like `viz.serve.make_server`, so the caller chooses the thread and
the tests can run it on an ephemeral port. Port 0 is the default for the same reason it is there: shared nodes
and fixed ports collide.

Owned by lane B.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `DEFAULT_HOST` |  |  |
| `MAX_BODY_BYTES` |  |  |
| `SESSION_ROUTE` |  |  |
| `logger` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`LiveHandler`](LiveHandler.md) | One request. |

## Functions

| Name | Summary |
|---|---|
| [`make_live_server`](make_live_server.md) | Bind (but do not run) the live-play server over `provider`. |
| [`run_live_server`](run_live_server.md) | Serve live play until interrupted — bind, print the banner (including the `ssh -L` line, reusing `viz.serve.serve_banner`'s form), then block in `serve_forever`. |
