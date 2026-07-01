<!-- [interp-refactor] session f80ef917 -->
# 03 · Participants & models

## The model registry

All model-keyed data lives in one place: [`chat/loading/registry.py`](../../chat/loading/registry.py). Short names resolve to an HF id + a **generation** (the behavior + tokenizer group); a raw HF id passes through unchanged.

```python
from experiments.core.chat import AutoModelParticipant
from experiments.core.chat.loading import MODELS, resolve, tokenizer_id

list(MODELS)                              # ['qwen2.5-0.5b', ..., 'gemma2-2b', 'gemma3-4b']
resolve("gemma3-4b")                      # ('google/gemma-3-4b-it', 'gemma3')
tokenizer_id("qwen2.5-3b")                # 'qwen2.5'  (same generation → tokenizer loaded once)
AutoModelParticipant.class_for("gemma2-2b")   # <class 'GemmaModelParticipant'>  (family-correct chat behavior)
```

(`AutoModelParticipant.class_for` is the public class resolver; `loading.participant_class` is the low-level primitive it delegates to.)

**Generation, not vendor, selects behavior.** `gemma2` and `gemma3` have *different* chat templates (Gemma 3 accepts a system role, Gemma 2 folds it into the first user turn), so each generation maps to its own participant class. Adding a model is one line in `MODELS`; adding a generation is one line in `GENERATIONS`. A slow test ([`tests/test_family_flags.py`](../../chat/tests/test_family_flags.py)) verifies the declared chat-template flags against each real tokenizer.

### Load weights directly

```python
import torch
from experiments.core.chat.loading import load_model
model, tok = load_model("qwen3-8b", device="cuda", dtype=torch.bfloat16, attn="flash_attention_2")
```

`load_model` shares a process-local cache: identical `(hf_id, device, dtype, attn, quant, revision)` returns the same model object; same-generation models share the tokenizer. Flash-attention is the default with automatic fallback to sdpa/eager; `quant="4bit"`/`"8bit"` is opt-in (perturbs activations → interp fidelity).

## `ModelParticipant` knobs

```python
from experiments.core.chat import AutoModelParticipant
p = AutoModelParticipant.from_pretrained(
    "qwen3-4b", name="p", device="cuda",
    load_kwargs={"attn": "sdpa"},   # optional: forwarded to load_model (dtype/attn/quant/revision)
    temperature=0.8, top_p=0.95, max_new_tokens=512,
    seed=1234,               # per-participant RNG seed → reproducible greedy/sampled turns (local models only)
    thinking="auto",         # "auto" defers to the template; True/False forces enable_thinking where supported
    system_prompt="…",
    kv_reuse="auto",         # cross-turn KV prefix reuse; see below
)
```

Already hold weights (e.g. sharing them, or an externally-loaded checkpoint)? Wrap them with `from_model`:

```python
from experiments.core.chat.loading import load_model
model, tok = load_model("qwen3-4b")
p = AutoModelParticipant.from_model(model, tok, name="p", id_or_name="qwen3-4b", temperature=0.8)
```

### `kv_reuse` (cross-turn KV cache)

`"auto"` (default) reuses the KV cache across a speaker's own consecutive turns when the new prompt exactly extends the cached tokens — skipping a full re-prefill. It is doubly guarded (exact-prefix check + safe fallback) and **auto-disables under steering/patch and batched generation**.

```python
p.kv_reuse = "auto"   # default: enabled when safe
p.kv_reuse = False    # force off — pin this for determinism-critical / reproducibility experiments,
                      #   since reuse can perturb outputs at the FP level vs a full prefill.
```

Enable `logging` at INFO to see the per-participant decision, DEBUG to see reuse engage per turn:

```python
import logging; logging.basicConfig(level=logging.INFO)
# INFO  ...model_participant: p: cross-turn KV reuse ENABLED (kv_reuse='auto')
```

## API-backed participants

`APIParticipant` is a full conversational participant with **no local model** — use it as an opponent, moderator, or judge. Interp requests (`capture`/`steering`/`patch`/`return_logprobs`) **raise** rather than silently no-op (a steering sweep that quietly did nothing would fabricate a "no effect" result).

```python
from experiments.core.chat import Conversation, APIParticipant, AutoModelParticipant

local = AutoModelParticipant.from_pretrained("qwen2.5-3b", name="student")
judge = APIParticipant(name="tutor", model_id="claude-sonnet-5", provider="anthropic",
                       system_prompt="You are a patient tutor. Ask one probing question per turn.",
                       max_tokens=400, temperature=1.0)

conv = Conversation(participants=(local, judge), shared_context="Teach the student about entropy.")
conv.run(turns=6)
```

Requires `ANTHROPIC_API_KEY` (or `ANTHROPIC_API_KEY_FILE`) and outbound network. For tests, inject a fake `client=callable(system, messages, model, max_tokens, temperature) -> str`.

Next: [context management & serialization](04_context_and_serialization.md).
