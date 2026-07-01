<!-- [interp-refactor] session f80ef917 -->
# 02 · Conversations in depth

`Conversation.from_models` is a convenience wrapper. Build a `Conversation` by hand when you want **per-speaker framing** (different system prompts / private context), a custom moderator, policies, or hooks.

## Build participants and a conversation manually

`AutoModelParticipant.from_pretrained(...)` is the HF-style loader (the participant analog of `AutoModelForCausalLM.from_pretrained`): it loads the model by id and returns the family-correct participant instance. Loading the same id twice shares one model object (weights are process-cached), so both speakers below share weights.

```python
from experiments.core.chat import Conversation, AutoModelParticipant

alice = AutoModelParticipant.from_pretrained(
    "qwen2.5-3b", name="alice", device="cuda",
    system_prompt="You are a concise, skeptical debater. Keep replies under 3 sentences.",
    temperature=0.7, max_new_tokens=200,
)
bob = AutoModelParticipant.from_pretrained(
    "qwen2.5-3b", name="bob", device="cuda",     # same id → shares alice's weights (cached)
    system_prompt="You are an enthusiastic optimist who loves analogies.",
    temperature=0.9, max_new_tokens=200,
)

conv = Conversation(
    participants=(alice, bob),
    shared_context="Topic: should cities ban cars downtown? Debate it.",  # seeded as a moderator turn
    shared_system_prompt="Stay respectful and on-topic.",                  # prepended to every speaker's system block
    reasoning_visibility="strip",   # see below
)
conv.run(turns=6)
```

### Framing ownership (who sees what)

- **Shared** framing lives on the `Conversation`: `shared_context` (injected once as a `moderator` turn everyone sees) and `shared_system_prompt` (merged into every speaker's system block).
- **Private** framing lives on each participant: `system_prompt` and `private_context` (a tuple of `ContextItem`) — invisible to the other speaker and to the transcript.

```python
from experiments.core.chat import ContextItem, AutoModelParticipant
spy = AutoModelParticipant.from_pretrained(
    "qwen2.5-3b", name="spy",
    system_prompt="Secretly steer the topic toward trains.",
    private_context=(ContextItem("Remember: never admit you have an agenda.", role_hint="user", author="handler"),),
)
```

## Turn-taking

- **`conv.step(speaker)`** — one turn by a specific speaker, committed to the transcript; returns the `Message` (or `None` if a [hook](06_hooks.md) denied it).
- **`conv.run(turns=N, until=..., first=...)`** — alternate speakers round-robin. `first` sets who starts.

```python
conv.step(alice)                        # drive turns explicitly
conv.step(bob)
conv.run(turns=4, first=alice)          # or in bulk
```

## Stopping

`until=` takes a single `StopCondition` or a list (any of which stops). Whichever of `turns`/`until` hits first ends the run.

```python
from experiments.core.chat import (
    TurnStopCondition, TokenStopCondition, ElapsedTimeStopCondition, StopStringCondition,
)

conv.run(until=[
    TurnStopCondition(max_turns=20),           # cap turns
    TokenStopCondition(max_tokens=4000),       # cap cumulative generated tokens
    ElapsedTimeStopCondition(seconds=120),     # wall-clock budget
    StopStringCondition(["I concede", "AGREED"]),  # stop when a turn contains any string
])
```

## Branching — fork a conversation for free

`branch()` forks into a new `Conversation` that **reuses the same participant objects** (shared weights, zero extra GPU) with a *copied* transcript. Explore divergent continuations without touching the original — each branch has its own transcript, so they diverge independently:

```python
base = conv.branch()
for _ in range(3):
    b = base.branch()
    b.run(turns=2, first="alice")     # first accepts a name, index, or Participant
    print("continuation:", b.transcript[-1].content[:80])
# `conv` and `base` are untouched; only each `b` advanced.
```

> Because branches **share the participant objects**, mutating a participant (e.g. `b.by_name["alice"].temperature = 0.3`) changes it for *every* branch and the original. To vary generation settings per branch, set them right before you run, or pin `seed` and vary only the prompt/intervention — see [09](09_advanced_interp_pipelines.md).

## Ephemeral sampling — read state without mutating it

`sample()` generates a reply to an optional temporary message **without committing anything** — ideal for probing "what would X say now?" repeatedly.

```python
for q in ["Summarize your position.", "What's your strongest objection?"]:
    print(conv.sample("alice", q, as_author="interviewer").content)
# conv.transcript is unchanged after all of this
```

`sample` and `step` accept the same interpretability options (`steering=`, `capture=`, `patch=`, `return_logprobs=`) — see [07](07_interp.md).

## Reasoning visibility (CoT models)

For models that emit `<think>…</think>`, `reasoning_visibility` controls whether a prior turn's parsed reasoning is re-injected into other speakers' views:

- `"strip"` (default) — reasoning never leaks into anyone's view.
- `"self_retain"` — a speaker sees only its *own* past reasoning.
- `"shared"` — everyone sees everyone's reasoning.

```python
from experiments.core.chat import ReasoningVisibility
conv = Conversation(participants=(alice, bob), reasoning_visibility=ReasoningVisibility.SELF_RETAIN)
```

The raw completion and parsed reasoning are always stored per message in `msg.metadata["raw_completion"]` / `msg.metadata["parsed_think"]`.

Next: [participant & model options](03_participants_and_models.md).
