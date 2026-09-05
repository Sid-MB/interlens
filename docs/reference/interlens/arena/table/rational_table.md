# `rational_table`

Every seat a computable policy: seat `i` plays `policies[i % len(policies)]` (cycled).

```python
rational_table(
	game: GameSpec,
	policies: list[str],
	*,
	deadline: int,
	full_info: bool = True,
	name: str = 'all_rational',
) -> SeatRouter
```

Defined in [`interlens.arena.table`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/table.py#L145-L153)

The
full-information :class:`GameTables` is built once and shared across seats.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameSpec](../negotiation/sheets/GameSpec.md) | *required* |  |
| `policies` | `list[str]` | *required* |  |
| `deadline` | `int` | *required* |  |
| `full_info` | `bool` | `True` |  |
| `name` | `str` | `'all_rational'` |  |
