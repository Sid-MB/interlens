# `table`

Module `interlens.arena.table`

Heterogeneous **tables**: present a whole many-seat lineup to the arena engine as one participant.

The engine drives ONE `Participant` across every seat of an episode — it asks the same object to speak for
each seat in turn. That is exactly right for a homogeneous table (one model plays everyone) and wrong for the
interesting cases: a different computable policy per seat, some LLM seats and some policy seats, or per-seat
model diversity. :class:`SeatRouter` closes the gap by dispatching each turn to the sub-participant that owns
that seat, using the seat identity the engine passes (`Participant.generate(..., seat=...)`, straight from
`SeatRequest.seat`).

The builders here compose a table from a game and a lineup, so seat assignment lives in one place rather than
being re-derived per experiment:

- :func:`policy_seat` — one computable-rational seat (a :class:`PolicyParticipant` bound to a named policy).
- :func:`rational_table` — every seat a policy, cycled from a list of policy names.
- :func:`mixed_table` — some seats given participants explicitly (LLM or otherwise), the rest filled with
  policy seats, so a partly-specified lineup is always complete.

Example:

```python
from interlens.arena.table import rational_table, mixed_table
from interlens.arena.negotiation import games

game, analysis, protocol_cfg = games.make_preset("divide_dollar", n_parties=3)
table = rational_table(game, ["boulware", "conceder", "tough"], deadline=game.rounds)
# or put a model in seat 0 and let policies fill the rest:
table = mixed_table(game, {0: my_model_participant}, deadline=game.rounds)
# hand `table` to EpisodePool.run_episode as the participant
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `OFFER_PREFIX` |  |  |
| `POLICY_FACTORIES` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`SeatRouter`](SeatRouter.md) | One participant that routes each turn to a per-seat sub-participant, so a single object presents a heterogeneous table to the arena engine. |

## Functions

| Name | Summary |
|---|---|
| [`mixed_table`](mixed_table.md) | A table where `assignment` maps a seat index to an already-built participant (e.g. an `AutoModelParticipant` or `APIParticipant` for an LLM seat) and every seat NOT in `assignment` is filled with a `fill_policy` seat — so a partly-specified lineup is always a complete table. |
| [`policy_seat`](policy_seat.md) | A computable-rational seat: a :class:`PolicyParticipant` bound to `policy_name` for seat `seat_idx`. |
| [`rational_table`](rational_table.md) | Every seat a computable policy: seat `i` plays `policies[i % len(policies)]` (cycled). |
