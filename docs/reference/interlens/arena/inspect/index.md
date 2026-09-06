# `inspect`

Package `interlens.arena.inspect`

Optional Inspect (inspect-ai) integration: run arena scenarios under `inspect eval`.

Install with the extra: `pip install interlens[inspect]`. Exposes the bundled scenarios as Inspect
`Task`s — instance banks as samples, the arena engine wrapped as a custom solver (any Inspect-supported
model plays every seat), and the exact scenario scorers as Inspect scorers:

```python
inspect eval interlens.arena.inspect/info_relay --model anthropic/claude-sonnet-5
```

See `tasks.py` for the task parameters (level, arm, situational cells, communication mode, instance count).

## Modules

- [`adapter`](adapter/index.md) — The Inspect adapter core: a Participant backed by Inspect's model, the arena solver, and the scorer.
- [`tasks`](tasks/index.md) — The bundled scenarios as Inspect tasks.

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`InspectModelParticipant`](adapter/InspectModelParticipant.md) | `interlens.arena.inspect.adapter` | An interlens `Participant` played by an Inspect model. |
| [`arena_solver`](adapter/arena_solver.md) | `interlens.arena.inspect.adapter` | Play one arena instance (from the sample's metadata) with the evaluated model in every seat. |
| [`coding_collab`](tasks/coding_collab.md) | `interlens.arena.inspect.tasks` | The coding-collaboration scenario as an Inspect task: 3 seats jointly write one Python module against a public pytest suite while each holds private style constraints; `level` sets how many constraints are dealt. |
| [`distributed_longcontext`](tasks/distributed_longcontext.md) | `interlens.arena.inspect.tasks` | A distributed long-context task as an Inspect task. |
| [`info_relay`](tasks/info_relay.md) | `interlens.arena.inspect.tasks` | The info-relay scenario (wrong-shard epistemics) as an Inspect task. |
| [`negotiation`](tasks/negotiation.md) | `interlens.arena.inspect.tasks` | The negotiation scenario as an Inspect task. |
| [`scenario_scorer`](adapter/scenario_scorer.md) | `interlens.arena.inspect.adapter` | Score from the scenario's exact outcome (stored by the solver): `success` (bool) and `primary` (the scenario's normalized primary metric), with the full outcome dict in the score metadata. |
| [`scorable`](tasks/scorable.md) | `interlens.arena.inspect.tasks` | The repaired `ScorableNegotiation` as an Inspect task, generated through the game-preset registry (:mod:`interlens.arena.negotiation.games`). |
| [`security_dilemma`](tasks/security_dilemma.md) | `interlens.arena.inspect.tasks` | The repeated security dilemma as an Inspect task: 12 rounds of message + simultaneous build/deescalate/attack waves with noisy intelligence; `level` sets the first-strike bonus and the observation-noise probability. |
