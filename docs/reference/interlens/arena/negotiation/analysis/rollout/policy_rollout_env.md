# `policy_rollout_env`

HOOK (unimplemented): bind the rational policies as rollout counterparts — `NegotiationState` as the env `State`, `ScorableNegotiation.apply` as the transition, each frozen counterpart a `policy(state)->action`.

```python
policy_rollout_env(scenario: Any, instance: Any)
```

Defined in [`interlens.arena.negotiation.analysis.rollout`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L102-L108)

The env-agnostic `counterfactual_regret`/`rollout` core is already tested via a synthetic env.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | `Any` | *required* |  |
| `instance` | `Any` | *required* |  |
