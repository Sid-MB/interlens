# `Conversation`

A multi-agent conversation: the recipe, the live dialogue, AND the benchmark-rollout driver, all in one lightweight object.

```python
Conversation(
	participants: tuple[Participant, ...],
	transcript: Transcript = Transcript(),
	shared_context: str | None = None,
	shared_system_prompt: str | None = None,
	moderator_name: str = 'moderator',
	context_policy: ContextPolicy = ErrorPolicy(),
	context_limit: int | None = None,
	reasoning_visibility: ReasoningVisibility = ReasoningVisibility.STRIP,
	execution_mode: ExecutionMode = ExecutionMode.THROUGHPUT,
	message_hooks: list = list(),
	communication: object = None,
)
```

Defined in [`interlens.conversation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L49-L726)

**Inherits from:** [Functional](../functional/Functional.md)

It orchestrates turn-taking between `Participant`s over a shared, perspective-neutral `Transcript`, owning
*who speaks when* and the **ordered view pipeline**: for each speaker it assembles a structured, typed view
(system block → private context → transcript turns), fits it to the context window on those typed segments,
then lets the participant flatten it (family fold/merge) and generate. Fitting *before* the lossy family
flatten is what lets the context policy preserve the system/moderator framing reliably (see `context/`).

Scenario framing is split by ownership: *shared* framing (`shared_context` as a moderator seed turn,
`shared_system_prompt`) lives here; *private* framing (`system_prompt`, `private_context`) lives on each
participant, so it is naturally invisible to the others and to the transcript.

**Copy-on-write + lazy.** Participants load their weights lazily, so an unrun `Conversation` is a cheap
recipe. Build it up functionally — `conv.turns(4).data(ds).analyzer(grade)` — where each dot-modifier
returns a modified *copy* (via `Functional.set`), never mutating the original; call `.set(field=value)` for
fields without a dot-modifier. `build`-free: run it directly with `run()`, or expand it over data / N
samples with `rollout()` (which copies it per row — see there).

Also supports branching (`branch()` / `branch_from()`), in-place history editing (`rewind()`, `edit()`,
`reset()`), ephemeral sampling (`sample()` / `sample_all()`), activation capture (`capture()`), and
disk persistence (`save()` / `load()`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `participants` | tuple[[Participant](../participant/participant/Participant.md), ...] | *required* |  |
| `transcript` | [Transcript](../transcript/Transcript.md) | `Transcript()` |  |
| `shared_context` | `str \| None` | `None` |  |
| `shared_system_prompt` | `str \| None` | `None` |  |
| `moderator_name` | `str` | `'moderator'` |  |
| `context_policy` | [ContextPolicy](../context/context_policy/ContextPolicy.md) | `ErrorPolicy()` |  |
| `context_limit` | `int \| None` | `None` |  |
| `reasoning_visibility` | [ReasoningVisibility](../reasoning_visibility/ReasoningVisibility.md) | `ReasoningVisibility.STRIP` |  |
| `execution_mode` | [ExecutionMode](../execution_mode/ExecutionMode.md) | `ExecutionMode.THROUGHPUT` |  |
| `message_hooks` | `list` | `list()` |  |
| `communication` | `object` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `communication` | `object` | Optional `CommunicationPolicy` governing turn order and message visibility (see `communication/`). |
| `context_limit` | `int \| None` | Token budget the `context_policy` fits to. |
| `context_policy` | [ContextPolicy](../context/context_policy/ContextPolicy.md) | How each speaker's view is fit to the context window — run on the typed segments *before* the family flatten so framing is preserved. |
| `execution_mode` | [ExecutionMode](../execution_mode/ExecutionMode.md) | The determinism-vs-throughput tension the runner consults: `THROUGHPUT` (default) permits batched co-stepping + KV reuse + flash-attn (only *distributional* reproducibility); `DETERMINISTIC` disables those for token-identical replay and interp fidelity. |
| `message_hooks` | `list` | Runtime-only middleware (**not** persisted): each hook vets / edits / denies a freshly generated message before it is committed. |
| `moderator_name` | `str` | Author name used for the `shared_context` seed and any moderator turns. |
| `participants` | tuple[[Participant](../participant/participant/Participant.md), ...] | The conversation's participants. |
| `reasoning_visibility` | [ReasoningVisibility](../reasoning_visibility/ReasoningVisibility.md) | Whether a prior turn's parsed `<think>` reasoning is re-injected into later views: `STRIP` (never), `SELF_RETAIN` (a speaker sees only its own), `SHARED` (everyone sees everyone's). |
| `row` | `dict` | The dataset row that produced this conversation in a data-driven `rollout` (the same dict the `dataset_field`s resolved against), or `{}` outside a rollout. |
| `shared_context` | `str \| None` | Scenario framing every participant sees, injected once as a leading `moderator_name` turn when the transcript starts empty. |
| `shared_system_prompt` | `str \| None` | A system prompt merged into every participant's system block (after that participant's private `system_prompt`). |
| `transcript` | [Transcript](../transcript/Transcript.md) | The shared, perspective-neutral message history. |

## Methods {#methods}

## `branch` {#branch}

```python
branch(self) -> 'Conversation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L466-L471)

Fork into a new `Conversation` that **reuses the same participant objects** (shared weights, zero GPU cost) with a copied, independent transcript.

The branch can diverge freely; the original is untouched. This
is exactly a no-op copy-on-write clone (`self.set()`). To fork from a specific point in the history rather
than the end, use `branch_from`.

## `branch_from` {#branch_from}

```python
branch_from(self, ref: MessageRef) -> 'Conversation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L473-L481)

Fork a new conversation whose history is this one's turns **up to and including** the turn `ref` — i.e. branch as if the conversation had stopped right after `ref`, ready for a different continuation.

`ref` is
a `MessageRef`: an `int` index (negatives count from the end) or the `Message` object itself (matched
by identity). The original is untouched; the fork shares participants (zero GPU cost).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `ref` | `MessageRef` | *required* |  |

## `capture` {#capture}

```python
capture(self, sites=('residual',), layers=None, offload: OffloadLocation = 'cpu')
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L304-L319)

Context manager that captures activations for every `step` inside the block into a fresh `ActivationCache`, auto-tagged by the current speaker + turn:

```python
with conv.capture(sites=["residual"], layers=[8, 12]) as cache:
        conv.step(bob)
cache.at(participant="bob", layer=12)
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sites` |  | `('residual',)` |  |
| `layers` |  | `None` |  |
| `offload` | `OffloadLocation` | `'cpu'` |  |

## `edit` {#edit}

```python
edit(
	self,
	ref: MessageRef,
	content: str | None = None,
	*,
	author: str | None = None,
	**metadata={},
) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L492-L497)

Edit a committed past turn in place and return it (see `Transcript.edit`): `ref` is a `MessageRef` (int index, negatives allowed, or a `Message` object matched by identity), and `content` / `author` / `**metadata` are the fields to change.

Editing the returned `Message`'s fields directly works too, since
the transcript holds it by reference.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `ref` | `MessageRef` | *required* |  |
| `content` | `str \| None` | `None` |  |
| `author` | `str \| None` | `None` |  |
| `metadata` |  | `{}` |  |

## `from_models` {#from_models}

```python
from_models(
	cls,
	models: tuple[ModelLike, ...],
	names: tuple[str, ...] = ('a', 'b'),
	device: str | torch.device | None = None,
	dtype: torch.dtype | None = None,
	shared_context: str | None = None,
	shared_system_prompt: str | None = None,
	prompt: PromptLike = None,
	**gen_kwargs={},
) -> 'Conversation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L176-L200)

Scaffold a conversation directly from a tuple of `models` — each an HF id or an already-loaded `PreTrainedModel` (see `ModelLike`).

Convenience wrapper around
`factories.conversation_from_models`; each model becomes a family-correct participant and `names` gives
them identities. **The order of `models` / `names` is the speaking order** — the first speaks first
unless you pass `first=` to `run`. `**gen_kwargs` are forwarded to every participant.

Scenario framing is available here too: `shared_system_prompt` (instructions, system role) and
`shared_context` (a neutral `moderator`-voiced opening seen by everyone). `prompt` is a separate
convenience for a *participant*-voiced opener (a `str` is attributed to the last participant). See that
function for the details.

`device` / `dtype` default to `None` here purely so this signature holds no second copy of the real
defaults (`"cuda"` / `bfloat16`, which live on `conversation_from_models`) — and so importing this
module does not need `torch` just to evaluate a default. `None` means "leave it to the factory".

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `models` | `tuple[ModelLike, ...]` | *required* |  |
| `names` | `tuple[str, ...]` | `('a', 'b')` |  |
| `device` | `str \| torch.device \| None` | `None` |  |
| `dtype` | `torch.dtype \| None` | `None` |  |
| `shared_context` | `str \| None` | `None` |  |
| `shared_system_prompt` | `str \| None` | `None` |  |
| `prompt` | `PromptLike` | `None` |  |
| `gen_kwargs` |  | `{}` |  |

## `load` {#load}

```python
load(cls, directory, devices='cuda') -> 'Conversation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L700-L726)

Rebuild a saved conversation: reconstruct (lazy) participants from the recipe and attach the saved transcript, resuming from that state (does NOT regenerate messages).

Raises on an unsupported schema.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `directory` |  | *required* |  |
| `devices` |  | `'cuda'` |  |

## `participant` {#participant}

```python
participant(self, which: ParticipantLike) -> Participant
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L436-L439)

Return one of this conversation's participants, resolved from a `Participant` object, its `name` (str), or its index (int).

Raises (via `_resolve_participant`) if it isn't in this conversation.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `which` | `ParticipantLike` | *required* |  |

## `render_templated` {#render_templated}

```python
render_templated(
	self,
	pov: ParticipantLike,
	*,
	extra=(),
	add_generation_prompt: bool = False,
	tokenize: bool = False,
)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L450-L462)

The full `view` run through `pov`'s tokenizer chat template — the **exact prompt its model sees**, special/control tokens and all (a str, or token ids with `tokenize=True`).

This is the truthful
counterpart to `transcript.render_templated`, which templates the transcript turns ONLY (no system /
private framing, no context-fit). Requires a local `ModelParticipant` (needs a tokenizer).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `pov` | `ParticipantLike` | *required* |  |
| `extra` |  | `()` |  |
| `add_generation_prompt` | `bool` | `False` |  |
| `tokenize` | `bool` | `False` |  |

## `reset` {#reset}

```python
reset(self) -> 'Conversation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L499-L507)

Return the conversation to its fresh, pre-`run` state: empty the transcript, then **re-seed** the `shared_context` moderator turn (exactly as `__post_init__` does on a fresh conversation).

Use this
rather than `transcript.clear()` when you want to rerun the same scenario — the raw `transcript.clear()`
drops the `shared_context` framing too, whereas `reset` restores it.

## `rewind` {#rewind}

```python
rewind(self, *, to: MessageRef) -> 'Conversation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L485-L490)

Rewind in place so the turn `to` becomes the new last turn, dropping everything after it (returns `self` for chaining).

`to` is a `MessageRef` (int index, negatives allowed, or a `Message` object).
Mutates this conversation — use `branch_from` instead to keep the original. See `Transcript.rewind`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `to` | `MessageRef` | *required* |  |

## `rollout` {#rollout}

```python
rollout(
	self,
	n: int | None = None,
	*,
	devices=None,
	out_dir=None,
	resume: bool = False,
	batched: bool = True,
	max_batch_size: int | None = None,
	seed: int | None = None,
) -> 'RunReport'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L626-L649)

Run many conversations from this one recipe and return a `RunReport` — the benchmark/scale entry point.

**Rollout does NOT mutate this conversation.** It makes an independent copy-on-write clone per job and runs
*those*; `self` stays the unrun recipe. Finished conversations live in `report.results[job_id].conversation`
(and their transcripts / analyses on the same `RunResult`) — that is where to `sample()` or inspect
afterwards, NOT on the original.

Two modes: with `data()` set, expands to ONE conversation per row (job ids `row_00000`…), resolving each
templated field (`dataset_field`) against the row; otherwise expands to `n` seeded copies of one scenario
(job ids `rollout_0000`…). `n` defaults to `len(data)`. Sample *i* gets `seed + i` (`seed` defaults
to the conversation's `seed` field). Any ambient `with StopCondition(...)` blocks and the `run_until`
field are captured now and attached to every job (so they survive the spawn boundary).

Parallel by default on two axes (see :func:`interlens.run`): one worker process per device, and batched
co-stepping within each device. `batched=False` gives the token-identical DETERMINISTIC path.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n` | `int \| None` | `None` |  |
| `devices` |  | `None` |  |
| `out_dir` |  | `None` |  |
| `resume` | `bool` | `False` |  |
| `batched` | `bool` | `True` |  |
| `max_batch_size` | `int \| None` | `None` |  |
| `seed` | `int \| None` | `None` |  |

## `run` {#run}

```python
run(
	self,
	turns: int | None = None,
	until: StopCondition | list | None = None,
	first: ParticipantLike | None = None,
	prompt: PromptLike = None,
) -> Transcript
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L321-L369)

Alternate speakers until `turns` elapse and/or a `StopCondition` fires (whichever comes first).

Speakers are taken in `participants` order (that tuple's order IS the turn order); `first` sets who
starts (default: `participants[0]`) and the rest follow round-robin. `first` may be a `Participant`,
its `name` (str), or its index (int) — resolved via `_resolve_participant` (raises if it isn't in this
conversation).

Stop conditions are combined from three sources (any of which stops the run): `until` (this call), the
conversation's own `run_until` field, and any ambient `with StopCondition(...):` blocks. A condition may
also cap each turn's tokens (`turn_cap`) — e.g. a `TokenBudget` shrinks the final turn to land on budget.
Conditions are `reset()` at the start so a reused instance doesn't leak state. `turns` defaults to the
conversation's `turns` field; at least one of turns / a stop condition must be present.

`prompt` (optional) is appended to the transcript **before** the run: a `str` is attributed to the LAST
participant (so `first` replies to it), a `Message` is appended as-is, `None` appends nothing. It
appends to the current end and never resets/reseeds.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `turns` | `int \| None` | `None` |  |
| `until` | [StopCondition](../stop/stop_condition/StopCondition.md) \| list \| None | `None` |  |
| `first` | `ParticipantLike \| None` | `None` |  |
| `prompt` | `PromptLike` | `None` |  |

## `sample` {#sample}

```python
sample(
	self,
	speaker,
	message=None,
	*,
	as_author=None,
	steering=None,
	capture=None,
	patch=None,
	return_logprobs: bool = False,
	max_new_tokens: int | None = None,
)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L518-L539)

Ephemerally sample a response **without mutating the transcript** — a pure read of current state, safe to call repeatedly / in a loop.

`speaker` is a `ParticipantLike` (name / index / `Participant`); pass a
**list or tuple** of them to sample each and get back `{name: Message}` instead of a single `Message`
(see also `sample_all`). `message` is an optional temporary incoming turn; it defaults to being
attributed to the **moderator** (a neutral, external voice — so "What do you think of Bob?" reads as an
interviewer asking, NOT as Bob speaking). Pass `as_author="bob"` to make it read as that participant's
turn instead (e.g. "what would you say if Bob had just said X?"). The same interp options as `step` are
honored on each ephemeral generation.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `speaker` |  | *required* |  |
| `message` |  | `None` |  |
| `as_author` |  | `None` |  |
| `steering` |  | `None` |  |
| `capture` |  | `None` |  |
| `patch` |  | `None` |  |
| `return_logprobs` | `bool` | `False` |  |
| `max_new_tokens` | `int \| None` | `None` |  |

## `sample_all` {#sample_all}

```python
sample_all(
	self,
	message: str | None = None,
	*,
	as_author: str | None = None,
	steering=None,
	capture=None,
	patch=None,
	return_logprobs: bool = False,
	max_new_tokens: int | None = None,
) -> 'dict[str, Message]'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L541-L548)

Ephemerally sample **every** participant's response — a convenience for `sample(list(self.participants), ...)`.

Returns `{name: Message}`; the transcript is untouched. Handy
for "what does each model say to this right now?".

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `str \| None` | `None` |  |
| `as_author` | `str \| None` | `None` |  |
| `steering` |  | `None` |  |
| `capture` |  | `None` |  |
| `patch` |  | `None` |  |
| `return_logprobs` | `bool` | `False` |  |
| `max_new_tokens` | `int \| None` | `None` |  |

## `save` {#save}

```python
save(self, directory) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L677-L698)

Persist the conversation: the transcript (`transcript.json`) + the recipe (`conversation.json` — the participants' own constructor kwargs + scenario framing/policies, no weights).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `directory` |  | *required* |  |

## `step` {#step}

```python
step(
	self,
	speaker: Participant,
	*,
	steering=None,
	capture=None,
	patch=None,
	return_logprobs: bool = False,
	max_new_tokens: int | None = None,
) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L275-L291)

Have `speaker` produce and commit one turn.

Interp options flow to `generate`; if no `capture` is
passed but a `conv.capture(...)` block is active, its pending request is used (auto-tagged by turn).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `speaker` | [Participant](../participant/participant/Participant.md) | *required* |  |
| `steering` |  | `None` |  |
| `capture` |  | `None` |  |
| `patch` |  | `None` |  |
| `return_logprobs` | `bool` | `False` |  |
| `max_new_tokens` | `int \| None` | `None` |  |

## `view` {#view}

```python
view(self, pov: ParticipantLike, extra=()) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/conversation.py#L441-L448)

The full `[{role, content}]` view `pov`'s model is conditioned on — the **real generation input**: system block (its private `system_prompt` + `shared_system_prompt`) → `private_context` → the transcript role-swapped to `pov`, then **context-fit** and **family-flattened**.

This is exactly what
`step` / `sample` feed to `generate`. Unlike `transcript.render_roles` (transcript turns only, no
framing or fitting), it reflects everything the model actually sees. `pov` is a `ParticipantLike` (name
/ index / participant); `extra` renders temporary, uncommitted messages (as `sample` does).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `pov` | `ParticipantLike` | *required* |  |
| `extra` |  | `()` |  |
