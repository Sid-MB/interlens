# `scorable_prompts`

Module `interlens.arena.scenarios.scorable_prompts`

The canonical prompt scaffold for the scorable-negotiation scenario.

Prompt configuration is a *documented confound*: in the scoreable-games literature the choice of
chain-of-thought scaffold swings the same model's success rate 15%->81% (Abdelnabi et al. 2309.17234) with
20-50 point swings across configs, and the best config is model-dependent (TMLR [Re] BVH81SAAh2). So this
module fixes exactly ONE canonical wording, and every knob that changes the wording is an explicit field on
:class:`PromptScaffold` — an experiment ablates prompt wording by constructing a variant scaffold, never by
editing the scenario. The scenario (:class:`~interlens.arena.scenarios.scorable.ScorableNegotiation`) holds a
scaffold and calls its render methods; :data:`DEFAULT_SCAFFOLD` is the blessed default.

Design rules baked in, each traceable to a peer-reviewed critique of the prior benchmarks:

- **Structural channel separation** (Lesson 11): a turn is one fenced JSON object with three fields —
  `scratchpad` (private, never published), `message` (public cheap talk), `action` (the formal move).
  The harness publishes ONLY `message` + a rendering of the validated `action`. Privacy never depends on
  the model's tag discipline, so a model that dumps its score numbers into `scratchpad` cannot leak them
  (numbers put in `message` are genuine strategic disclosure — a measured failure, not a parse artifact).
- **Formal votes, offer ids** (Lessons 7, 10): accepts reference a specific live offer id; a deal closes only
  by real unanimous ACCEPT of one standing offer, never by arithmetic on a final proposal.
- **Turn-count deadline restated every turn** (Lesson 13): `turn_prompt` always restates the round budget.
- **De-anchoring** (Lesson 5): issue/option labels come from the instance (fictional units), not from here.
- **Preference/role decorrelation knob** (Lesson 4): `role_lines` are OFF by default so public role text
  can't leak private preferences; turn on only to measure the leak.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ACTION_TYPES` |  |  |
| `DEFAULT_SCAFFOLD` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`PromptScaffold`](PromptScaffold.md) | One immutable prompt wording. |
