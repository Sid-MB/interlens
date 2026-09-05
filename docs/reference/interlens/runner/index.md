# `interlens.runner`

## Modules

- [`analyzer_registry`](analyzer_registry/index.md)
- [`batched`](batched/index.md)
- [`devices`](devices/index.md)
- [`pool`](pool/index.md) — The execution engine behind `Conversation.rollout` and `interlens.run`.
- [`worker_init`](worker_init/index.md)

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`RunReport`](pool/RunReport.md) | `interlens.runner.pool` | Aggregate outcome of a run. |
| [`RunResult`](pool/RunResult.md) | `interlens.runner.pool` | Outcome of one job: the finished `conversation` (weightless participants + completed transcript), its `transcript` and (serializable) `analysis`, or an `error` string if it failed. |
| [`available_devices`](devices/available_devices.md) | `interlens.runner.devices` | List the devices to spread conversations across: every CUDA GPU, else a single mps/cpu fallback. |
| [`register_analyzer`](analyzer_registry/register_analyzer.md) | `interlens.runner.analyzer_registry` |  |
| [`register_worker_init`](worker_init/register_worker_init.md) | `interlens.runner.worker_init` | Register a zero-arg callable to run once at worker startup (e.g. to populate the tool/analyzer registries). |
| [`resolve_analyzer`](analyzer_registry/resolve_analyzer.md) | `interlens.runner.analyzer_registry` | Accept either a callable (in-process) or a registered name (spawn-safe) and return the callable. |
| [`run`](pool/run.md) | `interlens.runner.pool` | Run several conversation lineups in ONE pool — the multi-lineup entry point (e.g. a ladder of model pairs × conditions in one overnight job). |
| [`run_jobs`](pool/run_jobs.md) | `interlens.runner.pool` | Run `(job_id, Conversation)` jobs across devices, with checkpointing, resume, and per-job failure isolation. |
| [`run_worker_init`](worker_init/run_worker_init.md) | `interlens.runner.worker_init` |  |
