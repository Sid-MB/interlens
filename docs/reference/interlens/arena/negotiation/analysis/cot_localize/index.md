# `cot_localize`

Module `interlens.arena.negotiation.analysis.cot_localize`

OmegaPRM-style within-CoT divergence localization: binary-search the first reasoning step that flips the
induced action to a divergent one, in O(log n) oracle calls (arXiv:2406.06592 — exploit prefix monotonicity:
correct until the first error, wrong after). Re-deriving an action from a truncated CoT is the LLM hook
(`induced_action_hook`); the search skeleton here is model-agnostic and tested against a synthetic oracle.

## Functions

| Name | Summary |
|---|---|
| [`induced_action_hook`](induced_action_hook.md) | HOOK (unimplemented): re-derive the action a truncated CoT induces by force-continuing the model from the joined `prefix_steps`; wrap with the oracle's divergence check to form `is_divergent` for `localize_first_divergence`. |
| [`localize_first_divergence`](localize_first_divergence.md) | Binary-search the earliest prefix length `j` (1..n_steps) whose induced action is divergent. |
| [`split_steps`](split_steps.md) | Split a CoT scratchpad into reasoning steps. |
