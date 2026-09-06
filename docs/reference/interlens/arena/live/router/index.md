# `router`

Module `interlens.arena.live.router`

`LiveSeatRouter`: a seat table whose occupants can change while the episode is running.

`SeatRouter` already presents a heterogeneous lineup to the engine as one participant. This subclass adds the
two things live play needs on top:

- **hot-swap.** :meth:`swap` replaces a seat's participant between turns. The engine holds a reference to the
  TABLE, not to the seat participants, so replacing an entry in the table is all it takes for the next turn to be
  played by somebody else — no episode restart, no engine involvement.
- **attribution.** Every message the table returns is stamped with the occupant label that produced it
  (`msg.metadata["occupant"]` -> `TurnRecord.occupant`), so the transcript records who played each turn
  rather than who holds the seat when you happen to read it.

The lock matters and is easy to get wrong. `generate` runs on an engine worker thread and `swap` on an HTTP
thread, so a swap can land at any instant. The rule: the participant AND its label are read together, once, under
the lock, and generation then runs OUTSIDE it against that snapshot. Reading them separately could stamp one
occupant's label on another's turn, which is the one failure that would make the occupant record a lie; holding
the lock across generation would instead block every swap for the length of an API call.

A swap therefore takes effect on the NEXT turn, never mid-turn. That is also why a swap is refused while the
seat's human prompt is open: the person is already answering, and the turn is theirs.

Owned by lane A.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `logger` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`LiveSeatRouter`](LiveSeatRouter.md) | A :class:`~interlens.arena.table.SeatRouter` that supports mid-episode occupant changes. |
