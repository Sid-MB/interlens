# `seat_swapped`

A seat changed occupant between turns.

```python
seat_swapped(
	seat: str,
	seat_idx: int,
	from_: str | None,
	to: str,
	at_turn: int,
) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L209-L214)

`from_`/`to` are occupant labels (`None` from-side if the
outgoing occupant was unlabelled) and `at_turn` is the turn index the new occupant starts at. JSON keys
are `from`/`to`; the parameter carries an underscore only because `from` is a keyword.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `seat_idx` | `int` | *required* |  |
| `from_` | `str \| None` | *required* |  |
| `to` | `str` | *required* |  |
| `at_turn` | `int` | *required* |  |
