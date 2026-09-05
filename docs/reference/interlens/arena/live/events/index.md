# `interlens.arena.live.events`

The live-play wire protocol: every server-sent event a session can emit, in one place.

This module is the SINGLE SOURCE OF TRUTH for what goes over the wire. The server never builds an event dict by
hand and the browser never reads a literal event name — both go through the constants and builders here — so the
protocol cannot drift between the two halves of a feature written by different people at the same time.

Transport is plain SSE over `GET /api/session/{sid}/events`. A frame is:

```python
id: <seq>
event: <type>
data: <one-line JSON>

(blank line)
```

`seq` is a monotonic per-session sequence number over ALL events the session emitted, and the session keeps the
emitted frames in a log, so a browser that reconnects sends `Last-Event-ID: <seq>` and is replayed everything
after it. That, not a heartbeat, is what makes a reload mid-episode lossless. `data` is always ONE line
(`json.dumps` with no newlines) because a bare newline inside `data` would be read as a field break by the
EventSource parser and split one event into two.

Builders return `(event_type, data_dict)` rather than a formatted frame: the session stamps the sequence number
when it appends to its log (that is where the ordering is decided), and :func:`format_sse` does the formatting.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `AWAITING_HUMAN` |  |  |
| `EPISODE_DONE` |  |  |
| `EPISODE_STARTED` |  |  |
| `ERROR` |  |  |
| `EVENT_TYPES` |  |  |
| `HELLO` |  |  |
| `INPUT_REJECTED` |  |  |
| `KEEPALIVE_FRAME` |  |  |
| `KEEPALIVE_SECONDS` |  |  |
| `LEGAL_ACTION_DEFAULTS` |  |  |
| `LOBBY_STATE` |  |  |
| `SEAT_SWAPPED` |  |  |
| `SSE_HEADERS` |  |  |
| `TURN_APPENDED` |  |  |
| `TURN_STARTED` |  |  |
| `UNKNOWN_TURN_IDX` |  |  |
| `USAGE` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`awaiting_human`](awaiting_human.md) | A human seat is blocked on input — everything the control dock renders from. |
| [`episode_done`](episode_done.md) | The episode ended. |
| [`episode_started`](episode_started.md) | An episode began. |
| [`error`](error.md) | Something failed. |
| [`format_sse`](format_sse.md) | Format one event as an SSE frame, ready to write to the socket. |
| [`hello`](hello.md) | Stream opened. |
| [`input_rejected`](input_rejected.md) | A human submission was refused before it reached the engine. |
| [`lobby_state`](lobby_state.md) | The lobby's full configuration: the chosen instance bank, framing and instance, the per-seat configs (`SeatConfig.to_json()` dicts, in seat order) and the session's spend cap in dollars. |
| [`seat_swapped`](seat_swapped.md) | A seat changed occupant between turns. |
| [`turn_appended`](turn_appended.md) | A committed, persisted turn. |
| [`turn_started`](turn_started.md) | A seat is being asked to move. |
| [`usage`](usage.md) | Spend so far against the cap. |
