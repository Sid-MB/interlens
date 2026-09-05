# `SeatRouter`

One participant that routes each turn to a per-seat sub-participant, so a single object presents a heterogeneous table to the arena engine.

```python
SeatRouter(seats: dict[str, Participant], name: str = 'seat_router')
```

Defined in [`interlens.arena.table`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/table.py#L71-L122)

**Inherits from:** [Participant](../../participant/participant/Participant.md)

Parameters
----------
seats : dict[str, Participant]
    Seat display name (`"Avery"`, `"Blake"`, ..., or a scenario's solo seat) to the participant that
    plays it. Interp requests are forwarded to the sub-participant, which accepts or refuses them per its own
    contract (a local-model seat can be captured/steered; a policy seat raises).
name : str
    Identifier within the conversation.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seats` | dict[str, [Participant](../../participant/participant/Participant.md)] | *required* |  |
| `name` | `str` | `'seat_router'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |
| `others_role` |  |  |
| `private_context` |  |  |
| `seats` |  |  |
| `self_role` |  |  |
| `system_prompt` |  |  |

## Methods {#methods}

## `generate` {#generate}

```python
generate(self, view, *, seat: str | None = None, **kwargs={}) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/table.py#L94-L100)

Dispatch to the participant owning `seat` and return its message unchanged.

`seat` comes from the engine (`SeatRequest.seat`). It is required: without it there is no reliable way
to know which seat this turn is for, and guessing from the prompt text silently breaks whenever the
wording changes — so a missing seat raises rather than picking a default.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `view` |  | *required* |  |
| `seat` | `str \| None` | `None` |  |
| `kwargs` |  | `{}` |  |

## `participant_for` {#participant_for}

```python
participant_for(self, seat: str | None)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/table.py#L102-L122)

The sub-participant that owns `seat`.

Declaring this method is how a table tells the batched engine "I am **pure dispatch** — you may address my
sub-participants directly". `BatchedEpisodePool` uses it to group a co-stepped wave by the participant
that will actually serve each request rather than by the table object, which is what makes a heterogeneous
lineup batchable at all: every episode gets its OWN table (policy seats hold per-episode state), so
grouping by table would put one request in each group and batch nothing, while grouping by owner collects
the model seats of every live episode — which DO share one cached model participant — into a single batch.

Only implement it on a table whose `generate` adds nothing of its own. A table that rewrites the view
per seat (a planner/advocate wrapper) must NOT expose this, or the engine would bypass that rewriting;
such a table supplies `generate_batch_with_seats` instead and keeps the whole wave.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str \| None` | *required* |  |
