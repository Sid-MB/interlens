# `security_dilemma`

The repeated security dilemma as an Inspect task: 12 rounds of message + simultaneous build/deescalate/attack waves with noisy intelligence; `level` sets the first-strike bonus and the observation-noise probability.

```python
security_dilemma(
	level: int = 0,
	n_instances: int = 10,
	seed0: int = 1,
	turn_max_tokens: int = 2048,
	token_limit: int | None = None,
) -> Task
```

Defined in [`interlens.arena.inspect.tasks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/inspect/tasks.py#L85-L100)

Team arm only (the game is irreducibly 2-party), round-robin protocol only
(a simultaneous-move payoff game has no sound free-messaging reduction).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | `0` |  |
| `n_instances` | `int` | `10` |  |
| `seed0` | `int` | `1` |  |
| `turn_max_tokens` | `int` | `2048` |  |
| `token_limit` | `int \| None` | `None` |  |
