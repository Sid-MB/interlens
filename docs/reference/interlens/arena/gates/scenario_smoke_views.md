# `scenario_smoke_views`

Real rendered views for gating: a fresh team state's first requests, plus the views after one scripted turn (so later views carry assistant/user mixes, which is where templates diverge).

```python
scenario_smoke_views(
	scenario: Scenario,
	*,
	level: int = 0,
	seed: int = 999101,
	scripted_turn: str = 'I suggest we start by sharing our goals.',
) -> list[list[dict]]
```

Defined in [`interlens.arena.gates`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/gates.py#L38-L48)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | [Scenario](../scenario/Scenario.md) | *required* |  |
| `level` | `int` | `0` |  |
| `seed` | `int` | `999101` |  |
| `scripted_turn` | `str` | `'I suggest we start by sharing our goals.'` |  |
