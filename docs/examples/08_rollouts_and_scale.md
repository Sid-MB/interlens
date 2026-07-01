<!-- [interp-refactor] session f80ef917 -->
# 08 · Rollouts & scale

Run one scenario many times, across many GPUs, checkpointed and resumable — with per-spec failure isolation (one OOM/bad spec can't take down the batch).

## `rollout` — N runs of one scenario

```python
from interlens import ConversationTemplate, ModelParticipantConfig, rollout

tmpl = ConversationTemplate(
    participants=[
        ModelParticipantConfig(name="a", model="qwen2.5-3b", temperature=0.9),
        ModelParticipantConfig(name="b", model="qwen2.5-3b", temperature=0.9),
    ],
    shared_context="Debate: tabs vs spaces.",
    turns=6,
)

report = rollout(
    tmpl, n=64, turns=6,
    devices=None,            # None → all visible GPUs (see available_devices()); or e.g. ["cuda:0","cuda:1"]
    out_dir="runs/tabs_spaces",   # checkpoints each conversation → resumable
    seed=0,                  # per-rollout seeds are seed, seed+1, …
    batched=True,            # co-step same-model rollouts in one batched generate (big throughput win)
)

for job_id, res in report.results.items():
    if res.error is None:
        print(job_id, "→", res.transcript[-1].content[:80])
print("failed:", report.failed, "skipped(resumed):", report.skipped)
```

`rollout` expands the template into `n` `ConversationSpec`s with distinct seeds/ids and hands them to `run_conversations`.

## `run_conversations` — heterogeneous specs

When the specs differ (different scenarios/models), build them yourself:

```python
from interlens import ConversationSpec, run_conversations, available_devices

specs = [
    ConversationSpec(template=tmpl_a, job_id="a_debate", turns=6),
    ConversationSpec(template=tmpl_b, job_id="b_debate", turns=8),
]
report = run_conversations(
    specs,
    devices=available_devices(),   # list of GPUs; one worker process per device (specs round-robined)
    out_dir="runs/mixed",
    resume=True,                   # skip specs already checkpointed in out_dir
    batched=False,
)
```

- **Single device (or `in_process=True`)** → runs sequentially in this process (the path used on non-multi-GPU machines, and the one where `analyze` can be a plain callable).
- **Multiple devices** → spawns one process per GPU (`torch.multiprocessing`, since fork+CUDA is broken). Specs and analyzers must therefore be resolvable *by name / serializable* (see below).

`RunReport`: `.results` (`{job_id: RunResult}`), `.failed` (errored ids), `.skipped` (resume-skipped). `RunResult`: `.transcript`, `.analysis`, `.error`, plus the device it ran on.

## `analyze` — measure each run while models are resident

`analyze(conv)` runs **inside the worker** right after the conversation finishes, while the models are still on-GPU — so it can `sample`, `branch`, or read activations on the live conversation. Only its **serializable return value** is kept (in `RunResult.analysis`).

```python
def summarize(conv):
    # e.g. ask each speaker for a one-word stance, without mutating the saved transcript
    return {
        "n_turns": len(conv.transcript),
        "a_stance": conv.sample("a", "One word: your final stance?").content.strip(),
        "b_stance": conv.sample("b", "One word: your final stance?").content.strip(),
    }

report = rollout(tmpl, n=32, turns=6, out_dir="runs/x", analyze=summarize)   # in-process: pass the callable
```

### Multi-GPU: register analyzers by name

Spawned workers inherit no parent state, so an analyzer that must run in the pool has to be **registered by name at import time** (a lambda/closure over parent locals can't cross the process boundary):

```python
from interlens import register_analyzer

def stance_probe(conv):
    return {"a": conv.sample("a", "One word stance?").content.strip()}

register_analyzer("stance_probe", stance_probe)   # at module import
report = run_conversations(specs, devices=available_devices(), analyze="stance_probe", out_dir="runs/x")
```

For heavy per-worker setup (e.g. loading a probe/classifier once per GPU), use `register_worker_init`.

## Execution modes & reproducibility

- **Batched co-stepping** (`batched=True`) trades exact per-row reproducibility for throughput — batch composition + a single global RNG perturb rows, so only *distributional* reproducibility holds. Batched turns are marked in `metadata["batched"]`; the shared-prefill fast path (turn 1 of a rollout off one scenario) in `metadata["shared_prefill"]`.
- For **exact** reproducibility, run unbatched with per-participant `seed=` and pin `kv_reuse=False`.

Next: [advanced interp pipelines](09_advanced_interp_pipelines.md).
