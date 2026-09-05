# `counterfactual_regret`

Roll `k` continuations from the model's action and from the oracle's action (both taken by `agent` at `state`, then everyone — including `agent` — follows `policies`) and report the mean-surplus gap.

```python
counterfactual_regret(
	env: RolloutEnv,
	state: State,
	agent: str,
	model_action: Action,
	oracle_action: Action,
	policies: dict[str, Policy],
	*,
	k: int = 8,
) -> CounterfactualRegret
```

Defined in [`interlens.arena.negotiation.analysis.rollout`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L80-L99)

With deterministic policies the k rollouts coincide and `k` is effectively 1; `k` matters once a policy
is stochastic (a mixed strategy or, later, an LLM counterpart at temperature). `policies` must include a
continuation policy for `agent` itself (its post-branch behavior).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `env` | [RolloutEnv](RolloutEnv.md) | *required* |  |
| `state` | `State` | *required* |  |
| `agent` | `str` | *required* |  |
| `model_action` | `Action` | *required* |  |
| `oracle_action` | `Action` | *required* |  |
| `policies` | `dict[str, Policy]` | *required* |  |
| `k` | `int` | `8` |  |
