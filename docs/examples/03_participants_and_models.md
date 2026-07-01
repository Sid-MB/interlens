<!-- [interp-refactor] session f80ef917 -->
# 03 · Participants & models

## How models resolve

There's **no registry and no short names** — you pass an **HF id** (or an already-loaded model), and interlens picks the family-correct participant class from the model's own **`config.model_type`** (exactly like HuggingFace `AutoModel`), then derives its chat-template flags by probing the tokenizer. Any model of a supported family Just Works:

```python
from interlens import AutoModelParticipant

p = AutoModelParticipant.from_pretrained("google/gemma-2-2b-it", name="p")      # -> GemmaModelParticipant
q = AutoModelParticipant.from_pretrained("Qwen/Qwen2.5-3B-Instruct", name="q")  # -> base ModelParticipant
```

**Family behavior is data-driven, not hand-declared.** Whether a template accepts a standalone system role or requires strictly alternating turns is **auto-derived from the tokenizer** (`interlens.loading.derive_chat_flags`), so e.g. Gemma 2 (folds system into the first user turn) and Gemma 3 (accepts a system role) are handled correctly with zero per-model config. Only families with a distinct *tool-call format* need a participant subclass — Gemma's `tool_code`, Llama's `<|python_tag|>`; **Qwen, Mistral, OLMo, Phi, DeepSeek, … all use the base participant automatically** (and a brand-new family/size resolves the moment it's on the Hub). A slow test ([`tests/test_family_flags.py`](../../tests/test_family_flags.py)) checks the derivation against real tokenizers.

### Load weights directly

```python
import torch
from interlens.loading import load_model
model, tok = load_model("Qwen/Qwen3-8B", device="cuda", dtype=torch.bfloat16, attn="flash_attention_2")
```

`load_model` shares a process-local cache: identical `(hf_id, device, dtype, attn, quant, revision)` returns the same model object; each HF id caches its own tokenizer. Flash-attention is the default with automatic fallback to sdpa/eager; `quant="4bit"`/`"8bit"` is opt-in (perturbs activations → interp fidelity).

## `ModelParticipant` knobs

```python
from interlens import AutoModelParticipant
p = AutoModelParticipant.from_pretrained(
    "Qwen/Qwen3-4B", name="p", device="cuda",
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
from interlens.loading import load_model
model, tok = load_model("Qwen/Qwen3-4B")
p = AutoModelParticipant.from_model(model, tok, name="p", temperature=0.8)   # family from model.config.model_type
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
from interlens import Conversation, APIParticipant, AutoModelParticipant

local = AutoModelParticipant.from_pretrained("Qwen/Qwen2.5-3B-Instruct", name="student")
judge = APIParticipant(name="tutor", model_id="claude-sonnet-5", provider="anthropic",
                       system_prompt="You are a patient tutor. Ask one probing question per turn.",
                       max_tokens=400, temperature=1.0)

conv = Conversation(participants=(local, judge), shared_context="Teach the student about entropy.")
conv.run(turns=6)
```

Requires `ANTHROPIC_API_KEY` (or `ANTHROPIC_API_KEY_FILE`) and outbound network. For tests, inject a fake `client=callable(system, messages, model, max_tokens, temperature) -> str`.

## Per-turn `max_new_tokens`

`temperature`/`top_p`/`seed` are set once per participant, but generation *length* often varies per turn (a one-word verdict vs a paragraph). `step`/`sample` take an optional `max_new_tokens` override for exactly that:

```python
conv.sample("a", "Answer in one word.", max_new_tokens=8)     # short
conv.step(conv.by_name["a"], max_new_tokens=400)              # long
```

Next: [context management & serialization](04_context_and_serialization.md).
