# `distributed_longcontext`

A distributed long-context task as an Inspect task.

```python
distributed_longcontext(
	instances: str,
	task_name: str | None = None,
	n_instances: int | None = None,
	arm: str = 'team',
	communication: str | None = None,
	token_limit: int | None = None,
) -> Task
```

Defined in [`interlens.arena.inspect.tasks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/inspect/tasks.py#L124-L162)

Instances embed megabytes of context and are built
offline (`interlens.arena.scenarios.dlc.build`); pass the saved bank as `-T instances=/path/to/
dlc_sniah_L0.json`. `task_name` overrides the task inferred from the bank's first instance.
`communication="messaging"` runs the scenario's NATIVE directed-messaging arm (`team-msg` — each
non-finalizer turn routes private fenced-JSON messages), not the generic mailbox variant, so episodes stay
replayable. Per-turn caps come from the task adapter (they are part of the task definition).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instances` | `str` | *required* |  |
| `task_name` | `str \| None` | `None` |  |
| `n_instances` | `int \| None` | `None` |  |
| `arm` | `str` | `'team'` |  |
| `communication` | `str \| None` | `None` |  |
| `token_limit` | `int \| None` | `None` |  |
