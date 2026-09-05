# `annotate`

Run every oracle over one decision point and return one inline :class:`OracleRecord` each — the ready helper a scenario calls from `annotate_turn` so its oracle wiring is a single line.

```python
annotate(
	oracles: Sequence[Oracle],
	game: Any,
	history: Sequence,
	agent: str,
	legal: Sequence,
	*,
	chosen_action: Any = None,
	round: int,
	seat: str,
	turn_idx: int = -1,
) -> list[OracleRecord]
```

Defined in [`interlens.arena.oracles`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L245-L258)

Skips an oracle that
raises (a broken oracle must not abort an episode).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `oracles` | Sequence[[Oracle](Oracle.md)] | *required* |  |
| `game` | `Any` | *required* |  |
| `history` | `Sequence` | *required* |  |
| `agent` | `str` | *required* |  |
| `legal` | `Sequence` | *required* |  |
| `chosen_action` | `Any` | `None` |  |
| `round` | `int` | *required* |  |
| `seat` | `str` | *required* |  |
| `turn_idx` | `int` | `-1` |  |
