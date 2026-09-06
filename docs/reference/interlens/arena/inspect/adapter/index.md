# `adapter`

Module `interlens.arena.inspect.adapter`

The Inspect adapter core: a Participant backed by Inspect's model, the arena solver, and the scorer.

Thin glue by design — Inspect owns model access, per-sample concurrency, retry, logging, and native
token-usage tracking; interlens owns the game (the SAME `EpisodePool`/`Scenario`/`MessagingPolicy`
machinery as outside Inspect — no duplicated engine). The bridge is one class: `InspectModelParticipant`, an
interlens `Participant` whose `generate` posts an `inspect_ai` model call back onto the event loop.
Because the arena engine already runs blocking participants in worker threads, the whole engine — episode
pooling, budgets, retries, provisional forking — works under Inspect unchanged, and Inspect's own
`--max-samples` concurrency runs many episodes at once (the solver holds no shared mutable state).

What the adapter adds on top of Inspect's native accounting: dollar cost per sample (`metadata['cost_usd']`,
priced by `interlens.usage` — Inspect tracks tokens natively but not dollars) and the arena outcome/usage
recorded in the sample store for the scorer and the viewer.

## Classes

| Name | Summary |
|---|---|
| [`InspectModelParticipant`](InspectModelParticipant.md) | An interlens `Participant` played by an Inspect model. |

## Functions

| Name | Summary |
|---|---|
| [`arena_solver`](arena_solver.md) | Play one arena instance (from the sample's metadata) with the evaluated model in every seat. |
| [`scenario_scorer`](scenario_scorer.md) | Score from the scenario's exact outcome (stored by the solver): `success` (bool) and `primary` (the scenario's normalized primary metric), with the full outcome dict in the score metadata. |
