# `turn_started`

A seat is being asked to move.

```python
turn_started(
	turn_idx: int,
	round_: int,
	phase: str,
	seat: str,
	seat_idx: int,
	occupant: str | None,
) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L153-L159)

`turn_idx` is the index the turn WILL take, `round_`/`phase` locate
it in the scenario, and `occupant` is who is answering (`None` when the seat's occupant is unlabelled).
Trailing underscore on `round_` only because `round` is a builtin; the JSON key is `round`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `turn_idx` | `int` | *required* |  |
| `round_` | `int` | *required* |  |
| `phase` | `str` | *required* |  |
| `seat` | `str` | *required* |  |
| `seat_idx` | `int` | *required* |  |
| `occupant` | `str \| None` | *required* |  |
