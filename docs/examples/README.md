<!-- [interp-refactor] session f80ef917 — examples index for interlens -->
# `interlens` — examples

Worked examples for the multi-model conversation + interpretability harness, ordered simple → advanced. Every snippet assumes you import the package as a library:

```python
from interlens import Conversation, AutoModelParticipant, ModelParticipant  # etc.
```

The import root is the repo root (`/juice2/u/siddharth/ii_mats`), i.e. run with the repo on `sys.path` — e.g. `uv run python your_script.py` or `uv run python -m ...` from the repo root. GPU examples need CUDA; a small model (`Qwen/Qwen2.5-0.5B-Instruct`) runs on CPU/MPS for smoke tests.

## What this library does

Orchestrates turn-taking between two (or more) **participants** — local HF models or hosted-API models — over a shared, perspective-neutral **transcript**, with first-class **interpretability** (activation capture, steering, activation patching, token logprobs) hooked into the *same* generation path as real turns. It scales from one interactive conversation to thousands of checkpointed, multi-GPU **rollouts**.

## The three layers of serialization / abstraction

1. **Live objects** — `Conversation` + `Participant`s you build and drive in-process ([01](01_quickstart.md), [02](02_conversations.md)).
2. **Template** — `ConversationTemplate` (participant *specs* + scenario framing, no messages): a serializable recipe you can rebuild, ship to workers, and run many times ([04](04_context_and_serialization.md), [08](08_rollouts_and_scale.md)).
3. **Saved conversation** — template + transcript on disk, resumable ([04](04_context_and_serialization.md)).

## Index

| # | File | Covers |
|---|------|--------|
| 01 | [Quickstart](01_quickstart.md) | Two models talk in ~5 lines; read the transcript |
| 02 | [Conversations](02_conversations.md) | Manual builds, private/shared framing, moderator, turn-taking, stop conditions, `branch`, ephemeral `sample`, reasoning visibility |
| 03 | [Participants & models](03_participants_and_models.md) | Model resolution (config.model_type, auto-derived flags), `ModelParticipant` knobs, `kv_reuse`, `APIParticipant`, mixed local+API |
| 04 | [Context & serialization](04_context_and_serialization.md) | Context policies, templates, `save`/`load`, resume |
| 05 | [Tools](05_tools.md) | Define a `Tool`, register it, the tool-calling loop |
| 06 | [Hooks](06_hooks.md) | `MessageHook` approve / deny / edit (the LLM-judge seam) |
| 07 | [Interpretability](07_interp.md) | Capture, steering, ablation, patching, logprobs |
| 08 | [Rollouts & scale](08_rollouts_and_scale.md) | `rollout`, `run_conversations`, multi-GPU, batched co-stepping, `analyze`, checkpoint/resume |
| 09 | [Advanced interp pipelines](09_advanced_interp_pipelines.md) | Causal tracing (capture→patch across branches), steering sweeps, probe-in-the-loop `analyze` |

Related: the pipeline **performance** profiler lives at [`../../tests/profile_pipeline.py`](../../tests/profile_pipeline.py); model registry + flags at [`../../src/interlens/loading/registry.py`](../../src/interlens/loading/registry.py).
