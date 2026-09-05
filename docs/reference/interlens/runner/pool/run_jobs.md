# `run_jobs`

Run `(job_id, Conversation)` jobs across devices, with checkpointing, resume, and per-job failure isolation.

```python
run_jobs(
	jobs,
	devices=None,
	out_dir=None,
	resume=False,
	batched=True,
	max_batch_size=None,
) -> RunReport
```

Defined in [`interlens.runner.pool`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/pool.py#L141-L161)

Parallel by default on **two** axes: one worker **process per device** (jobs round-robined; multi-GPU spawns via
`torch.multiprocessing` since fork+CUDA is broken — a single device runs in-process), and within each device
**batched co-stepping** (`batched=True`). Jobs are grouped by co-step schedule signature so same-schedule jobs
batch into one `model.generate` — correct for ANY mix. `batched=False` gives the DETERMINISTIC path.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `jobs` |  | *required* |  |
| `devices` |  | `None` |  |
| `out_dir` |  | `None` |  |
| `resume` |  | `False` |  |
| `batched` |  | `True` |  |
| `max_batch_size` |  | `None` |  |
