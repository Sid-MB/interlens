# `mixed_table`

A table where `assignment` maps a seat index to an already-built participant (e.g. an `AutoModelParticipant` or `APIParticipant` for an LLM seat) and every seat NOT in `assignment` is filled with a `fill_policy` seat — so a partly-specified lineup is always a complete table.

```python
mixed_table(
	game: GameSpec,
	assignment: dict[int, Participant],
	*,
	deadline: int,
	full_info: bool = True,
	fill_policy: str = 'bayes-rational',
	name: str = 'mixed',
) -> SeatRouter
```

Defined in [`interlens.arena.table`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/table.py#L156-L168)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameSpec](../negotiation/sheets/GameSpec.md) | *required* |  |
| `assignment` | dict[int, [Participant](../../participant/participant/Participant.md)] | *required* |  |
| `deadline` | `int` | *required* |  |
| `full_info` | `bool` | `True` |  |
| `fill_policy` | `str` | `'bayes-rational'` |  |
| `name` | `str` | `'mixed'` |  |
