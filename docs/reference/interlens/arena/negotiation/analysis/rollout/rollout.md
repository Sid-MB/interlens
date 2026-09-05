# `rollout`

Drive `state` to a terminal state, each seat acting by its policy in `policies`.

```python
rollout(
	env: RolloutEnv,
	state: State,
	policies: dict[str, Policy],
	*,
	max_steps: int = 500,
) -> State
```

Defined in [`interlens.arena.negotiation.analysis.rollout`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L51-L61)

`max_steps` guards
against a non-terminating env (a policy that never closes).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `env` | [RolloutEnv](RolloutEnv.md) | *required* |  |
| `state` | `State` | *required* |  |
| `policies` | `dict[str, Policy]` | *required* |  |
| `max_steps` | `int` | `500` |  |
