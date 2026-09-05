# `info_relay`

The info-relay scenario (wrong-shard epistemics) as an Inspect task.

```python
info_relay(
	level: int = 0,
	n_instances: int = 10,
	seed0: int = 1,
	arm: str = 'team',
	communication: str | None = None,
	n_rounds: int | None = None,
	framing: str | None = None,
	honest_persona: str | None = None,
	wrong_persona: str | None = None,
	turn_max_tokens: int = 2048,
	token_limit: int | None = None,
	messaging_turns: int = 24,
) -> Task
```

Defined in [`interlens.arena.inspect.tasks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/inspect/tasks.py#L60-L82)

`communication` selects the
autonomous messaging variant (the scenario default) or the published round-robin protocol (the mode the
shipped v0 dataset used); the situational knobs mirror the scenario's `cfg`. `token_limit` (per
sample) is Inspect's native enforcement of an episode budget.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | `0` |  |
| `n_instances` | `int` | `10` |  |
| `seed0` | `int` | `1` |  |
| `arm` | `str` | `'team'` |  |
| `communication` | `str \| None` | `None` |  |
| `n_rounds` | `int \| None` | `None` |  |
| `framing` | `str \| None` | `None` |  |
| `honest_persona` | `str \| None` | `None` |  |
| `wrong_persona` | `str \| None` | `None` |  |
| `turn_max_tokens` | `int` | `2048` |  |
| `token_limit` | `int \| None` | `None` |  |
| `messaging_turns` | `int` | `24` |  |
