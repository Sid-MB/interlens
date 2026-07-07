<!-- [interp-refactor] session f80ef917 — examples index for interlens -->
# `interlens` — examples

Worked examples for the multi-model conversation + interpretability harness, ordered simple → advanced. Every snippet assumes you import the package as a library:

```python
from interlens import Conversation, AutoModelParticipant, ModelParticipant  # etc.
```

Install the package first (`pip install interlens`, or `pip install -e .` from the library root for development), then run any snippet as a normal script — e.g. `python your_script.py`. GPU examples need CUDA; a small model (`Qwen/Qwen2.5-0.5B-Instruct`) runs on CPU/MPS for smoke tests.

## What this library does

Orchestrates turn-taking between two (or more) **participants** — local HF models or hosted-API models — over a shared, perspective-neutral **transcript**, with first-class **interpretability** (activation capture, steering, activation patching, token logprobs) hooked into the *same* generation path as real turns. It scales from one interactive conversation to thousands of checkpointed, multi-GPU **rollouts**.

## One object: recipe = live dialogue = rollout driver

A `Conversation` (with lazy `Participant`s) is at once the serializable **recipe**, the **live dialogue** you drive in-process, and the **rollout driver** you expand over data/N samples. There are no separate template/spec/config types — build it up functionally (`.turns(6).data(ds).analyzer(grade)`), run it, or `.rollout()` it ([01](01_quickstart.md), [02](02_conversations.md), [08](08_rollouts_and_scale.md)). Persist it with `save`/`load` (recipe + transcript on disk, resumable — [04](04_context_and_serialization.md)).

## Index

| # | File | Covers |
|---|------|--------|
| 01 | [Quickstart](01_quickstart.md) | Two models talk in ~5 lines; read the transcript |
| 02 | [Conversations](02_conversations.md) | Manual builds, private/shared framing, moderator, turn-taking, stop conditions, `branch`, ephemeral `sample`, reasoning visibility |
| 03 | [Participants & models](03_participants_and_models.md) | Model resolution (config.model_type, auto-derived flags), `ModelParticipant` knobs, `kv_reuse`, `APIParticipant`, mixed local+API |
| 04 | [Context & serialization](04_context_and_serialization.md) | Context policies, the conversation-as-recipe, `save`/`load`, resume |
| 05 | [Tools](05_tools.md) | Define a `Tool`, register it, the tool-calling loop |
| 06 | [Hooks](06_hooks.md) | `MessageHook` approve / deny / edit (the LLM-judge seam) |
| 07 | [Interpretability](07_interp.md) | Capture, steering, ablation, patching, logprobs |
| 08 | [Rollouts & scale](08_rollouts_and_scale.md) | `conv.rollout`, data-driven rollouts (`dataset_field`), `interlens.run` (multi-lineup), `TokenBudget` (matched compute), multi-GPU, batched co-stepping, `analyzer`, checkpoint/resume |
| 09 | [Advanced interp pipelines](09_advanced_interp_pipelines.md) | Causal tracing (capture→patch across branches), steering sweeps, probe-in-the-loop `analyze` |

Related: the pipeline **performance** profiler lives at [`tests/profile_pipeline.py`](https://github.com/Sid-MB/interlens/blob/main/tests/profile_pipeline.py); the family self-registry lives on [`ModelParticipant`](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py) (`MODEL_TYPES` + `for_model_type`), and model loading / chat-flag derivation in [`load.py`](https://github.com/Sid-MB/interlens/blob/main/src/interlens/loading/load.py).
