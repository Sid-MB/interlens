# `coding_collab`

The coding-collaboration scenario as an Inspect task: 3 seats jointly write one Python module against a public pytest suite while each holds private style constraints; `level` sets how many constraints are dealt.

```python
coding_collab(
	level: int = 0,
	n_instances: int = 10,
	seed0: int = 1,
	arm: str = 'team',
	communication: str | None = None,
	turn_max_tokens: int = 2048,
	token_limit: int | None = None,
	messaging_turns: int = 24,
) -> Task
```

Defined in [`interlens.arena.inspect.tasks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/inspect/tasks.py#L103-L121)

Scoring runs the sandboxed test suite + AST constraint checks. The default messaging mode scores
the latest complete ```python fence in the sends as the submission; pass `"round_robin"` for the
published protocol (the mode the shipped v0 dataset used).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | `0` |  |
| `n_instances` | `int` | `10` |  |
| `seed0` | `int` | `1` |  |
| `arm` | `str` | `'team'` |  |
| `communication` | `str \| None` | `None` |  |
| `turn_max_tokens` | `int` | `2048` |  |
| `token_limit` | `int \| None` | `None` |  |
| `messaging_turns` | `int` | `24` |  |
