# `LiveSeatRouter`

A :class:`~interlens.arena.table.SeatRouter` that supports mid-episode occupant changes.

```python
LiveSeatRouter(
	seats: dict[str, Any],
	labels: dict[str, str] | None = None,
	on_turn_start: Callable[[str, str | None], None] | None = None,
	name: str = 'live_table',
)
```

Defined in [`interlens.arena.live.router`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/router.py#L53-L134)

**Inherits from:** [SeatRouter](../../table/SeatRouter.md)

Parameters
----------
seats : dict[str, Participant]
    Seat display name to the participant that starts the episode in it.
labels : dict[str, str] | None
    Seat display name to its occupant label (`"api:claude-fable-5"`, `"human:sid"`, ...). Seats missing
    from the map are stamped with nothing, which is how a turn records "unlabelled occupant" rather than
    guessing one.
on_turn_start : callable | None
    `on_turn_start(seat, occupant) -> None`, called just BEFORE dispatching a turn. This is the hook the
    live page's "who is thinking" indicator is driven from: it fires while the model call is in flight, which
    is the only moment the information exists and the only moment it is useful. Exceptions from it must not
    reach the engine — a broken indicator cannot be allowed to kill a game.
name : str
    Identifier within the conversation.

Notes
-----
Drive a live table with `EpisodePool`, never `BatchedEpisodePool`. The batched pool resolves a
pure-dispatch table (one declaring `participant_for`, which this inherits) to its sub-participants and
addresses them directly — which would bypass this class's `generate` and with it the occupant stamp, so a
hot-swapped episode would come back with no record of who played what. Live play issues one request per wave
anyway, so there is nothing to batch.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seats` | `dict[str, Any]` | *required* |  |
| `labels` | `dict[str, str] \| None` | `None` |  |
| `on_turn_start` | `Callable[[str, str \| None], None] \| None` | `None` |  |
| `name` | `str` | `'live_table'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `labels` |  |  |
| `on_turn_start` |  |  |

## Methods {#methods}

## `generate` {#generate}

```python
generate(self, view, *, seat: str | None = None, **kwargs={}) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/router.py#L92-L109)

Snapshot (participant, label) for `seat` under the lock, fire `on_turn_start`, generate outside the lock, and return the message with `metadata["occupant"]` set to the snapshotted label.

The label is stamped only when the participant did not set one itself, so a participant that knows better
than the table who it is (a human seat naming the player) keeps its own attribution.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `view` |  | *required* |  |
| `seat` | `str \| None` | `None` |  |
| `kwargs` |  | `{}` |  |

## `occupants` {#occupants}

```python
occupants(self) -> dict[str, str | None]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/router.py#L130-L134)

The current seat -> occupant-label map, read under the lock.

What `hello` reports so a page that
just connected badges seats correctly without replaying the whole swap history.

## `swap` {#swap}

```python
swap(self, seat: str, participant: Any, label: str) -> str | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/router.py#L111-L128)

Install `participant` as `seat`'s occupant from the next turn on.

Returns the label of the
occupant that was replaced (`None` if it had none), which the caller reports as the `from` side of a
`seat_swapped` event.

Raises `KeyError` for an unknown seat. Does NOT check whether a human prompt is open on that seat — the
session enforces that, because it is the half that knows the session's phase.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `participant` | `Any` | *required* |  |
| `label` | `str` | *required* |  |
