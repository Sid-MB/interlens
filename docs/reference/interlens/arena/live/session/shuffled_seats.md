# `shuffled_seats`

Permute WHO plays which seat, leaving the seats themselves alone.

```python
shuffled_seats(
	seats: list[SeatConfig],
	rng: random.Random,
) -> tuple[list[SeatConfig], list[int]]
```

Defined in [`interlens.arena.live.session`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L114-L144)

Returns the new lineup and the permutation that produced it as source indices: `order[i]` is the index the
seat now at position `i` came from, so `new[i] is seats[order[i]]` and `order` is what gets recorded.
Seat NAMES and parties do not move — Avery is still party 0 with party 0's score sheet — only the occupant
configurations do, which is the thing worth randomizing when seat position carries a protocol advantage (the
proposer order rotates from the proposer base, so "the model always opens" is a property of the lineup, not
of the model).

Uniform over permutations, re-drawn while the resulting ARRANGEMENT is the one it started from (see
:data:`SHUFFLE_REDRAWS`) — so it is uniform over the arrangements that visibly differ, and returns the input
unchanged, with the identity order, when no different arrangement exists.

Parameters
----------
seats : list[SeatConfig]
    The current lineup, in seat order.
rng : random.Random
    The source of randomness, passed in rather than reached for so a caller can make a shuffle reproducible
    (and so the test can pin an exact permutation instead of asserting that something moved).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seats` | list[[SeatConfig](../provider/SeatConfig.md)] | *required* |  |
| `rng` | `random.Random` | *required* |  |
