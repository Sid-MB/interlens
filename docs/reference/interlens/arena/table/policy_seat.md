# `policy_seat`

A computable-rational seat: a :class:`PolicyParticipant` bound to `policy_name` for seat `seat_idx`.

```python
policy_seat(
	policy_name: str,
	seat_idx: int,
	game: GameSpec,
	*,
	deadline: int,
	full_info: bool = True,
	tables: GameTables | None = None,
) -> PolicyParticipant
```

Defined in [`interlens.arena.table`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/table.py#L125-L142)

`full_info` (a FULL-information game) attaches the exact :class:`GameTables` so full-info policies (e.g.
the Bayesian best-responder) compute exactly; a PRIVATE game passes `tables=None` so the policy relies on
its belief model instead. The per-round `discount` is read off the game (its single source of truth). Deals
are emitted and decoded by issue/option NAME straight off `game.space`, matching the scenario transcript.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `policy_name` | `str` | *required* |  |
| `seat_idx` | `int` | *required* |  |
| `game` | [GameSpec](../negotiation/sheets/GameSpec.md) | *required* |  |
| `deadline` | `int` | *required* |  |
| `full_info` | `bool` | `True` |  |
| `tables` | [GameTables](../negotiation/oracle_context/GameTables.md) \| None | `None` |  |
