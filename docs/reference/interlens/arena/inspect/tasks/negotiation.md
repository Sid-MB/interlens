# `negotiation`

The negotiation scenario as an Inspect task.

```python
negotiation(
	level: int = 0,
	n_parties: int | None = None,
	n_instances: int = 10,
	seed0: int = 1,
	arm: str = 'team',
	coherent: bool = True,
	communication: str | None = None,
	n_rounds: int | None = None,
	stakes: str | None = None,
	personas: str | None = None,
	turn_max_tokens: int = 2048,
	token_limit: int | None = None,
	messaging_turns: int = 24,
) -> Task
```

Defined in [`interlens.arena.inspect.tasks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/inspect/tasks.py#L165-L202)

`n_parties` switches to the sweep generator (3-8 seats,
fixed deal space); otherwise the 6-party difficulty ladder at `level` (`coherent` per the role-prior
table). `communication` defaults to the scenario's messaging mode; pass `"round_robin"` for the
published protocol (the mode the shipped v0 dataset used). `stakes`/`personas`/`n_rounds` mirror the
scenario's situational config.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | `0` |  |
| `n_parties` | `int \| None` | `None` |  |
| `n_instances` | `int` | `10` |  |
| `seed0` | `int` | `1` |  |
| `arm` | `str` | `'team'` |  |
| `coherent` | `bool` | `True` |  |
| `communication` | `str \| None` | `None` |  |
| `n_rounds` | `int \| None` | `None` |  |
| `stakes` | `str \| None` | `None` |  |
| `personas` | `str \| None` | `None` |  |
| `turn_max_tokens` | `int` | `2048` |  |
| `token_limit` | `int \| None` | `None` |  |
| `messaging_turns` | `int` | `24` |  |
