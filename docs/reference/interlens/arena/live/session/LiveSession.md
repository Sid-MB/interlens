# `LiveSession`

One live episode plus its subscribers.

```python
LiveSession(
	sid: str,
	provider: ScenarioProvider,
	game: PreparedGame,
	seats: list[SeatConfig],
	run_dir: Any,
	budget_usd: float | None = None,
)
```

Defined in [`interlens.arena.live.session`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L147-L591)

Parameters
----------
sid : str
    Session id, used in every route and echoed in `hello`.
provider : ScenarioProvider
    Where games and model seats come from.
game : PreparedGame
    The assembled game this session plays (from `provider.prepare`).
seats : list[SeatConfig]
    Who plays each seat at the start, in seat order.
run_dir : str | Path
    Where the episode JSON is written. The live page links to it, and it is the durable artifact: the stream
    is a view of the file, never a replacement for it.
budget_usd : float | None
    Hard spend cap for this session, enforced by a `UsageMeter`. Required whenever any seat is a metered
    model — a live game with a human in it can idle for a long time with an API seat configured, and an
    uncapped session is how a lobby click turns into a bill.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sid` | `str` | *required* |  |
| `provider` | [ScenarioProvider](../provider/ScenarioProvider.md) | *required* |  |
| `game` | [PreparedGame](../provider/PreparedGame.md) | *required* |  |
| `seats` | list[[SeatConfig](../provider/SeatConfig.md)] | *required* |  |
| `run_dir` | `Any` | *required* |  |
| `budget_usd` | `float \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `budget_usd` |  |  |
| `episode_id` | `str \| None` | The running episode's id, or `None` until the first wave lands. |
| `game` |  |  |
| `meter` |  |  |
| `occupants` | `dict` | The current seat -> occupant-label map, or `{}` before the table is built. |
| `phase` |  |  |
| `provider` |  |  |
| `run_dir` |  |  |
| `seats` |  |  |
| `seq` | `int` | The sequence number of the last event this session emitted (0 before any). |
| `sid` |  |  |

## Methods {#methods}

## `broadcast` {#broadcast}

```python
broadcast(self, event: str, data: dict) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L423-L445)

Append one event to the session log under the next sequence number and push it to every subscriber.

Returns the sequence number assigned. Never blocks: it is called from the engine thread between turns, so
a subscriber whose queue is full is dropped rather than allowed to stall the game.

This is also where the session's own phase is kept: the events that move it (a seat blocking on a person,
a turn landing, the episode ending) are exactly the events that go over the wire, so reading the phase off
the stream keeps `/state` and the stream from ever disagreeing about where the session is.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `event` | `str` | *required* |  |
| `data` | `dict` | *required* |  |

## `lobby` {#lobby}

```python
lobby(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L499-L510)

This session's own configuration, in the shape the `lobby_state` event carries.

Carries the provider's `models` and `policies` listings as well as the current lineup, because the
live page's swap dock reuses the lobby's seat editor and must be able to offer the same choices without a
second round trip to `/api/lobby`.

## `snapshot` {#snapshot}

```python
snapshot(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L481-L497)

The session's complete current state, for a page load or a reload mid-episode.

`{seq, payload, phase, awaiting, occupants, lobby}` — where `payload` is a full
`viz.episode_payload` over the live episode's `to_json()` and `seq` is the sequence number that
payload is current as of, so the client subscribes with `Last-Event-ID: seq` and misses nothing. Using
the visualizer's own payload builder (rather than a live-specific one) is what guarantees a reloaded page
and a streamed one are showing the same thing.

## `start` {#start}

```python
start(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L238-L263)

Build the table, spawn the engine thread, and return the episode id.

Constructs each seat from its :class:`SeatConfig` (model seats through `provider.build_model_seat`,
computable seats through `arena.table.policy_seat`, human seats as `HumanParticipant`), wraps them in
a :class:`~interlens.arena.live.router.LiveSeatRouter`, and runs the episode with `on_wave` bound to
:meth:`_on_wave`. Fails fast — BEFORE the thread starts — if a configured API seat has no credentials or
a metered seat has no budget cap, so a misconfiguration surfaces in the lobby instead of as a dead game.

Returns the episode id, which is `""` until the engine mints one (see :attr:`episode_id`).

## `stop` {#stop}

```python
stop(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L340-L357)

End the session: unblock any waiting human seat, ask the engine thread to wind down, and broadcast `episode_done{status:"stopped"}`.

Idempotent — a double-click on Stop must not raise.

A blocked human seat is released immediately (its `generate` raises, and the engine finalizes the
episode as an error, which is the honest record: a stopped game did not play itself out). A seat that is
mid-generation cannot be interrupted — an API call in flight is in flight — so a stopped session ends
when that turn returns, and `episode_done` is broadcast then rather than optimistically now.

## `submit_human` {#submit_human}

```python
submit_human(self, seat: str, form: dict) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L378-L395)

Validate a human submission and hand it to the blocked seat.

Raises `ValueError` (message shown to the player) if the seat is not waiting, or the move is illegal /
unparseable / empty. Nothing is enqueued on a rejection: the seat stays blocked and the caller answers
400 and broadcasts `input_rejected`. This is the guard that keeps a typo from becoming a silent pass —
the engine would read empty content as a well-formed no-op turn.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `form` | `dict` | *required* |  |

## `subscribe` {#subscribe}

```python
subscribe(self, last_event_id: int | None = None) -> Any
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L463-L473)

Attach a client.

Returns a `queue.Queue` of `(seq, event, data)` tuples, pre-loaded with every
logged event after `last_event_id` — the replay that makes a reconnect lossless.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `last_event_id` | `int \| None` | `None` |  |

## `swap_seat` {#swap_seat}

```python
swap_seat(self, seat_idx: int, config: SeatConfig) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L397-L420)

Replace a seat's occupant, effective on its next turn.

Builds the new participant from `config`, installs it via the router, and broadcasts `seat_swapped`.
Refused (`ValueError`) while that seat's human prompt is open: the person is mid-decision and the turn
is already theirs. v1 applies swaps between turns only.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat_idx` | `int` | *required* |  |
| `config` | [SeatConfig](../provider/SeatConfig.md) | *required* |  |

## `unsubscribe` {#unsubscribe}

```python
unsubscribe(self, q: Any) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L475-L479)

Detach a client's queue (its SSE connection closed).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `q` | `Any` | *required* |  |
