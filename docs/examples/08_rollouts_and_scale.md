<!-- [interp-refactor] session f80ef917 -->
# 08 · Rollouts & scale

Run one scenario many times, across many GPUs, checkpointed and resumable — with per-spec failure isolation (one OOM/bad spec can't take down the batch).

## `rollout` — N runs of one scenario

```python
from interlens import ConversationTemplate, ModelParticipantConfig, rollout

tmpl = ConversationTemplate(
    participants=[
        ModelParticipantConfig(name="a", model="Qwen/Qwen2.5-3B-Instruct", temperature=0.9),
        ModelParticipantConfig(name="b", model="Qwen/Qwen2.5-3B-Instruct", temperature=0.9),
    ],
    shared_context="Debate: tabs vs spaces.",
    turns=6,
)

report = rollout(
    tmpl, n=64, turns=6,
    devices=None,            # None → all visible GPUs (see available_devices()); or e.g. ["cuda:0","cuda:1"]
    out_dir="runs/tabs_spaces",   # checkpoints each conversation → resumable
    seed=0,                  # per-rollout seeds are seed, seed+1, …
    # batched=True is the DEFAULT: local models always co-step in one batched generate (max throughput, no
    # per-model opt-out). Pass batched=False only for the DETERMINISTIC/interp escape hatch (see below).
)

for job_id, res in report.results.items():
    if res.error is None:
        print(job_id, "→", res.transcript[-1].content[:80])
print("failed:", report.failed, "skipped(resumed):", report.skipped)
```

`rollout` expands the template into `n` `ConversationSpec`s with distinct seeds/ids and hands them to `run_conversations`.

> **Runnable example — evaluate on a real benchmark.** [`examples/gsm8k_benchmark_rollout.py`](../../examples/gsm8k_benchmark_rollout.py) runs a solver/critic conversation over GSM8K (one spec per problem) and reports accuracy — the end-to-end pattern for the heterogeneous case below.

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
    # batched=True by default: specs are grouped by schedule signature, so same-schedule specs (e.g. all
    # problems of one benchmark) batch together and a truly mixed lineup splits into its own group — always safe.
)
```

- **Parallel by default on two axes**: one worker *process per device*, AND *batched co-stepping* within each device. No flag needed — batching groups specs by their co-step schedule (turns + per-position model identity), so heterogeneous specs still batch correctly (each distinct lineup forms its own group; a one-off lineup runs as a singleton = per-conv).
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

## Large API rollouts (batch mode)

For rollouts of hosted models (`APIParticipant`), set `batch=True` on the participant to route each round's turns through the provider's **asynchronous batch API** — ~50% cost and much higher throughput/rate limits, at the price of batch-window latency (minutes–hours, polled). The default `batched=True` co-stepper collects each round's same-position turns across all `n` rollouts into **one** provider batch submission:

```python
from interlens import ConversationTemplate, APIParticipantConfig, rollout

tmpl = ConversationTemplate(
    participants=[
        APIParticipantConfig(name="pro", provider="openai",    model_id="gpt-5",           batch=True, system_prompt="Argue YES."),
        APIParticipantConfig(name="con", provider="anthropic", model_id="claude-sonnet-5", batch=True, system_prompt="Argue NO."),
    ],
    shared_context="Is a hot dog a sandwich?", turns=4,
)
report = rollout(tmpl, n=200, turns=4)   # each round → one Anthropic/OpenAI batch per speaker
```

- **Batch APIs exist only for `provider="anthropic"` and `provider="openai"`.** Requesting `batch=True` on `provider="openrouter"` **raises** (OpenRouter has no batch endpoint) — it never silently degrades to serial calls, so a requested batch discount is never quietly dropped.
- With `batch=False` (default) API turns run as ordinary concurrent single requests, bounded by the shared client's max-in-flight semaphore.
- You can also batch outside a rollout: `participant.generate_batch(views)` or, at the client level, `client.submit_batch(requests)`.

See [participants & models](03_participants_and_models.md) for provider setup + API keys.

## Execution modes & reproducibility

- **Batched co-stepping is the default** (`batched=True`): local `ModelParticipant`s (every family — qwen/gemma/llama/…) always co-step, trading exact per-row reproducibility for throughput — batch composition + a single global RNG perturb rows, so only *distributional* reproducibility holds. Batched turns are marked in `metadata["batched"]`; the shared-prefill fast path (turn 1 of a rollout off one scenario) in `metadata["shared_prefill"]`.
- `batched=False` is the **`ExecutionMode.DETERMINISTIC`** escape hatch: each rollout runs independently and is **token-identical** on the same hardware (pin per-participant `seed=` and `kv_reuse=False`). It is the only path that supports per-turn interp (capture/steering/probes) — batched generation cannot. Use it only when you need exact replay or interp, not merely to run local models (which always maximize throughput otherwise).

Next: [advanced interp pipelines](09_advanced_interp_pipelines.md).
