# `session`

Module `interlens.arena.live.session`

`LiveSession`: one live game — the engine thread, the event log, and everything the browser can do to it.

A session owns a running episode and the fanout to however many browsers are watching it. Its threading model is
small on purpose, because a live server with an LLM in it has enough moving parts already:

- ONE engine thread per session runs `asyncio.run(EpisodePool(...).run_episode(...))` with `max_concurrent=1`.
  The negotiation scenario issues exactly one request per wave, so turns are strictly sequential — which is what
  makes a turn-by-turn UI honest rather than a reordering of a concurrent batch.
- HTTP threads (one per request, from `ThreadingHTTPServer`) mutate the session: submit a human move, swap a
  seat, stop. Every mutation takes ONE `threading.RLock`.
- Streaming is a plain fanout: :meth:`broadcast` appends the event to a sequence-numbered log and
  `put_nowait`s it on each subscriber's queue. It never blocks and never waits on a socket, because it is
  called from the engine thread — a slow reader must be able to fall behind or be dropped, never to stall a game.

No asyncio primitives are shared across threads. The engine thread has its own event loop and the only things
crossing the boundary are `queue.Queue` handoffs, which are thread-safe by construction. Cross-loop asyncio
objects are the classic way this goes wrong and are simply not used.

The event log is what makes reload lossless: a reconnecting browser replays from `Last-Event-ID` and a fresh
one renders :meth:`snapshot` server-side, then subscribes from the snapshot's sequence number.

Owned by lane B.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `DEFAULT_BUDGET_USD` |  |  |
| `INSTRUCTION_HEADER` |  |  |
| `PHASES` |  |  |
| `SHUFFLE_REDRAWS` |  |  |
| `SUBSCRIBER_QUEUE_MAX` |  |  |
| `logger` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`LiveSession`](LiveSession.md) | One live episode plus its subscribers. |
| [`SessionManager`](SessionManager.md) | The server's session registry. v1 holds ONE active session at a time. |

## Functions

| Name | Summary |
|---|---|
| [`apply_private_instructions`](apply_private_instructions.md) | Append `instructions` to `participant`'s `private_context` as one labelled segment, and return it. |
| [`shuffled_seats`](shuffled_seats.md) | Permute WHO plays which seat, leaving the seats themselves alone. |
