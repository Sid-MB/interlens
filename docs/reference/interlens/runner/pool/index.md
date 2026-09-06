# `pool`

Module `interlens.runner.pool`

The execution engine behind `Conversation.rollout` and `interlens.run`.

A *job* is a `(job_id, Conversation)` pair — an unrun, fully-resolved conversation (lazy participants, no
dataset). `run_jobs` runs a list of them across devices with checkpointing, resume, per-job failure isolation,
and (by default) batched co-stepping within each device. Each finished conversation is returned on its
`RunResult` so it can be sampled/inspected afterwards. The analyzer travels ON each conversation
(`conv._analyzer`) — a callable in-process, or a registered name across a spawn boundary.

## Classes

| Name | Summary |
|---|---|
| [`RunReport`](RunReport.md) | Aggregate outcome of a run. |
| [`RunResult`](RunResult.md) | Outcome of one job: the finished `conversation` (weightless participants + completed transcript), its `transcript` and (serializable) `analysis`, or an `error` string if it failed. |

## Functions

| Name | Summary |
|---|---|
| [`run`](run.md) | Run several conversation lineups in ONE pool — the multi-lineup entry point (e.g. a ladder of model pairs × conditions in one overnight job). |
| [`run_jobs`](run_jobs.md) | Run `(job_id, Conversation)` jobs across devices, with checkpointing, resume, and per-job failure isolation. |
