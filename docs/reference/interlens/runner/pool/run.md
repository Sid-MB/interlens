# `run`

Run several conversation lineups in ONE pool — the multi-lineup entry point (e.g. a ladder of model pairs × conditions in one overnight job).

```python
run(
	conversations,
	devices=None,
	out_dir=None,
	resume=False,
	batched=True,
	max_batch_size=None,
) -> RunReport
```

Defined in [`interlens.runner.pool`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/pool.py#L164-L180)

Each conversation is expanded to its jobs (one per `data()` row if it has data, else a single conversation),
with job ids namespaced by that conversation's `name` (default `conv{i}`) so ids stay unique and resumable.
All jobs go into one pool, so GPUs stay packed across lineups (no idle tail between sequential rollouts) under a
single `out_dir`/resume namespace, returning one merged `RunReport`. Mixing lineups is safe: batched
co-stepping groups by schedule signature, so each distinct lineup forms its own batch group.

`Conversation.rollout` is the single-lineup sugar for this (`run([conv], ...)`-equivalent via `run_jobs`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversations` |  | *required* |  |
| `devices` |  | `None` |  |
| `out_dir` |  | `None` |  |
| `resume` |  | `False` |  |
| `batched` |  | `True` |  |
| `max_batch_size` |  | `None` |  |
