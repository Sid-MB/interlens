<!-- [interp-refactor] session f80ef917 -->
# 04 · Context management & serialization

## Context-window policies

Long conversations overflow the model's context. A `ContextPolicy` decides what to keep. Crucially it runs on the **typed segments** (system / moderator / private_context / turns) *before* the family flatten, so framing is preserved reliably.

```python
from interlens import (
    Conversation, ErrorPolicy, DropOldestPolicy, SlidingWindowPolicy, SummarizePolicy,
)

# ErrorPolicy (default): raise if the view exceeds context_limit — never silently truncate.
conv = Conversation(participants=(alice, bob), context_policy=ErrorPolicy(), context_limit=8192)

# SlidingWindowPolicy: keep framing + the most recent `keep_last` turns; drop older ones.
conv = Conversation(participants=(alice, bob), context_policy=SlidingWindowPolicy(keep_last=8))

# DropOldestPolicy: drop oldest turns until it fits (needs context_limit).
conv = Conversation(participants=(alice, bob), context_policy=DropOldestPolicy(), context_limit=8192)

# SummarizePolicy: replace older middle turns with a summary; keep framing + last `keep_last` verbatim.
conv = Conversation(
    participants=(alice, bob),
    context_policy=SummarizePolicy(keep_last=4, summarizer=lambda turns: "Earlier: " + " | ".join(turns)),
)
```

`context_limit=None` (default) means the tokenizer's own `model_max_length` is used.

## Serialization: the three levels

### Level 2 — `ConversationTemplate` (recipe, no messages)

A serializable spec: participant configs + scenario framing + policies. This is what rollouts expand and workers rebuild.

```python
from interlens import ConversationTemplate, ModelParticipantConfig, APIParticipantConfig, SlidingWindowPolicy

tmpl = ConversationTemplate(
    participants=[
        ModelParticipantConfig(name="alice", model="Qwen/Qwen2.5-3B-Instruct", temperature=0.7, system_prompt="Be terse."),
        ModelParticipantConfig(name="bob", model="google/gemma-2-2b-it", temperature=0.9),
    ],
    shared_context="Debate: is a hotdog a sandwich?",
    shared_system_prompt="Stay civil.",
    turns=6,
    context_policy=SlidingWindowPolicy(keep_last=8),
    reasoning_visibility="strip",
)

tmpl.save("scenario.json")                       # round-trips through JSON
tmpl2 = ConversationTemplate.load("scenario.json")

conv = tmpl.build(devices="cuda")                # → live Conversation (loads the models)
conv.run(turns=tmpl.turns)
```

`ModelParticipantConfig` mirrors the `ModelParticipant` knobs (`dtype`, `attn`, `quant`, `revision`, `max_new_tokens`, `temperature`, `top_p`, `seed`, `thinking`, `tool_names`, `max_tool_iters`, `kv_reuse`, `weights_path`).

Go from a live conversation back to a template with `conv.to_template()`.

### Level 3 — save/load a whole conversation (template + transcript)

```python
conv.save("runs/debate_001")                     # writes template.json + transcript.json
resumed = Conversation.load("runs/debate_001", devices="cuda")   # reloads models, ATTACHES the transcript
resumed.run(turns=4)                             # continues from where it left off (does not regenerate)
```

`build`/`load` take `devices=` as a single device or a list (participants are round-robined across the list — handy for putting two big models on two GPUs).

Next: [tools](05_tools.md) · [hooks](06_hooks.md) · [interpretability](07_interp.md) · [rollouts](08_rollouts_and_scale.md).
