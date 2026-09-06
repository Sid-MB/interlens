# `negotiation`

Module `interlens.arena.scenarios.negotiation`

Negotiation: a multi-issue, multi-party deal with secret score sheets (structured-JSON actions).

n seats (default 6) negotiate 5 issues (3-4 options each). Each seat holds a secret per-issue score sheet and
all share an acceptance threshold. Turns are round-robin; a seat may speak freely and optionally register a
complete proposal and/or declare support for a registered one via a fenced JSON action. Early termination:
after any full round in which all non-adversarial seats support the same proposal, that deal is final.
Otherwise, after the last round the proposer registers one final binding proposal.

A deal passes iff proposer ≥ threshold AND veto ≥ threshold AND ≥ n-1 of n seats ≥ threshold.
`primary` = joint_score(deal) / max_feasible_joint if passed else 0. The generator enumerates the full deal
space exactly, so every instance ships with its exact ceiling, feasible-set size, and hidden optimum.

Two solver-verified generators:

- `generate_instance(level, seed, coherent=True)` — the 6-party difficulty ladder (feasible-set size shrinks
  with level). `coherent=True` (default) permutes each seat's sheet so its own-best options are never ones
  its role stereotypically disfavors (see `priors.py`) — no character-vs-payoff tension. `coherent=False`
  reproduces the original experiments' incoherent instances.
- `generate_instance_n(n_parties, seed)` — the situational-sweep generator: 3-8 parties over the SAME fixed
  issue set (so party count is not confounded with deal-space size), feasible-set size held at the base
  ladder's fraction of the deal space.

Situational config (the `cfg` dict passed to `make_state`) varies the *situation* around the fixed game:
`n_rounds` (round-robin rounds before the forced final), `stakes` (narrative dollar framing — the sheets
are identical), `personas` (disposition wording per seat's private block: `"pragmatic"` / `"altruistic"`
/ `"greedy"` for all, `"one_greedy"`, or `"mixed"`).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `DEAL_SPACE` |  |  |
| `FRAC_BUCKET` |  |  |
| `ISSUES` |  |  |
| `LEVEL_BUCKETS` |  |  |
| `N_TURN_ROUNDS` |  |  |
| `PERSONA_TEXT` |  |  |
| `PROVISIONAL_TURN_MARKS` |  |  |
| `ROLES_POOL` |  |  |
| `STAKES` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`Negotiation`](Negotiation.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`persona_assignment`](persona_assignment.md) | Per-seat disposition labels for a persona cell spec. |
