# `interlens.arena.inspect.tasks`

The bundled scenarios as Inspect tasks.

Each task generates a solver-verified instance bank (deterministic in `seed0`), exposes it as samples (the
full instance JSON + situational config in sample metadata, per-seat framings included), plays each sample
with the evaluated model in every seat via `arena_solver`, and scores with the scenario's exact scorer.
Episode-level budgets map to Inspect's native per-sample limits where an equivalent exists (`token_limit`
carries the episode token budget so Inspect enforces and displays it); arena-specific accounting (dollar cost,
per-seat usage) is enforced in the solver and reported in sample metadata/score metadata — one budget
definition, two enforcement surfaces.

Run e.g.:

```python
inspect eval interlens.arena.inspect/info_relay --model anthropic/claude-sonnet-5 -T level=2 -T cell=wrong_confident
inspect eval interlens.arena.inspect/negotiation --model openai/gpt-5 -T arm=solo
```

## Functions

| Name | Summary |
|---|---|
| [`coding_collab`](coding_collab.md) | The coding-collaboration scenario as an Inspect task: 3 seats jointly write one Python module against a public pytest suite while each holds private style constraints; `level` sets how many constraints are dealt. |
| [`distributed_longcontext`](distributed_longcontext.md) | A distributed long-context task as an Inspect task. |
| [`info_relay`](info_relay.md) | The info-relay scenario (wrong-shard epistemics) as an Inspect task. |
| [`negotiation`](negotiation.md) | The negotiation scenario as an Inspect task. |
| [`scorable`](scorable.md) | The repaired `ScorableNegotiation` as an Inspect task, generated through the game-preset registry (:mod:`interlens.arena.negotiation.games`). |
| [`security_dilemma`](security_dilemma.md) | The repeated security dilemma as an Inspect task: 12 rounds of message + simultaneous build/deescalate/attack waves with noisy intelligence; `level` sets the first-strike bonus and the observation-noise probability. |
