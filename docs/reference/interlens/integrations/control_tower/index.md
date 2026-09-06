# `control_tower`

Module `interlens.integrations.control_tower`

Run a local Interlens participant behind Control Tower's untrusted-policy boundary.

Control Tower loads :func:`interlens_untrusted_policy` as an external `module:function` policy. The returned
generate function has Inspect's normal model signature, so blue protocols see and control every generated tool
call. Interlens owns local generation and interpretability; Control Tower owns tool execution, monitoring,
auditing, sandboxing, and trajectory storage.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `InterlensGenerateFn` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`interlens_attack_policy`](interlens_attack_policy.md) | Control Tower attack policy backed by an Interlens local participant. |
| [`interlens_team_policy`](interlens_team_policy.md) | Control Tower policy backed by a private Interlens planner-reviewer-executor team. |
| [`interlens_untrusted_policy`](interlens_untrusted_policy.md) | Control Tower external untrusted policy backed by a local Interlens participant. |
| [`participant_generate`](participant_generate.md) | Adapt one local Interlens participant to Inspect's model-generation protocol. |
| [`team_participant_generate`](team_participant_generate.md) | Adapt one local participant as a private planner-reviewer-executor team. |
