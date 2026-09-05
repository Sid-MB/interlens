# `interlens.arena.negotiation.analysis.rollout`

Counterfactual-rollout regret: label a divergence by Δ expected surplus, not by action mismatch. At turn t,
roll k continuations from the model's action and from the oracle's action against the *same frozen counterpart
policies* and score the gap in the acting party's expected surplus (mismatch alone over-labels — many actions
are near-optimal). Engine-agnostic: works against a small `RolloutEnv` protocol + a per-seat `Policy` map;
`policy_rollout_env` is the (unimplemented) hook to bind `ScorableNegotiation` + the rational policies.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `Action` |  |  |
| `Policy` |  |  |
| `State` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`CounterfactualRegret`](CounterfactualRegret.md) | Δ expected surplus between the oracle action and the model action for the acting `agent`: positive = the oracle's action leads to more surplus (a real divergence), 0 = the model's action was as good. |
| [`RolloutEnv`](RolloutEnv.md) | The negotiation transition a rollout needs. |

## Functions

| Name | Summary |
|---|---|
| [`counterfactual_regret`](counterfactual_regret.md) | Roll `k` continuations from the model's action and from the oracle's action (both taken by `agent` at `state`, then everyone — including `agent` — follows `policies`) and report the mean-surplus gap. |
| [`policy_rollout_env`](policy_rollout_env.md) | HOOK (unimplemented): bind the rational policies as rollout counterparts — `NegotiationState` as the env `State`, `ScorableNegotiation.apply` as the transition, each frozen counterpart a `policy(state)->action`. |
| [`rollout`](rollout.md) | Drive `state` to a terminal state, each seat acting by its policy in `policies`. |
