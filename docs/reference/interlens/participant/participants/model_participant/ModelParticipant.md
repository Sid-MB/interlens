# `ModelParticipant`

A conversation participant backed by a local HuggingFace causal LM.

```python
ModelParticipant(
	name: str = '',
	hf_id: str | None = None,
	weights_path: str | None = None,
	adapter_path: str | None = None,
	dtype: str = 'bfloat16',
	attn: str = 'flash_attention_2',
	quant: str | None = None,
	revision: str | None = None,
	device: str | torch.device | None = None,
	max_new_tokens: int = 512,
	temperature: float = 0.8,
	top_p: float = 0.95,
	seed: int | None = None,
	thinking: bool | str = 'auto',
	system_prompt: str | None = None,
	private_context: tuple = (),
	tools: tuple = (),
	max_tool_iters: int = 4,
	kv_reuse: bool | str = 'auto',
	steering: object = None,
)
```

Defined in [`interlens.participant.participants.model_participant`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L73-L689)

**Inherits from:** [Functional](../../../functional/Functional.md), [Participant](../../participant/Participant.md)

Generation flow: the `Conversation` hands us a `view` — the transcript rendered from *our* perspective,
already context-fitted and flattened by `finalize_view` into `[{role, content}]`. We apply this model's
own chat template to it, generate, decode only the newly produced tokens, and split any `<think>`
reasoning out of the visible content. Only the visible answer becomes `Message.content`;
the parsed reasoning and raw completion live in `metadata` under neutral keys, so hidden generated text is
never fed back into other participants' views (it's stripped from history automatically because
`render_roles` uses `content`).

**The participant is its own recipe.** It stores *what to load* (`hf_id` + dtype/attn/quant/revision) and
loads the weights **lazily on first use** through the process-wide model cache — so an unrun participant is
cheap (KBs), pickles across a spawn boundary without shipping weights, and `.set(...)` copies share one
loaded model object by reference (the co-stepping batch win). `model`/`tokenizer` are properties that
trigger the load; the raw `model` is exposed deliberately (interp experiments register forward hooks on it).
Weight loads are keyed on `(hf_id, device, dtype, attn, quant, revision)` and cached, so all same-recipe
participants on one device share ONE object. Build via `from_pretrained` (lazy) or `from_model` (eager,
from an already-loaded model); `.set()` (from `Functional`) makes copy-on-write clones with fresh KV state.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | `''` |  |
| `hf_id` | `str \| None` | `None` |  |
| `weights_path` | `str \| None` | `None` |  |
| `adapter_path` | `str \| None` | `None` |  |
| `dtype` | `str` | `'bfloat16'` |  |
| `attn` | `str` | `'flash_attention_2'` |  |
| `quant` | `str \| None` | `None` |  |
| `revision` | `str \| None` | `None` |  |
| `device` | `str \| torch.device \| None` | `None` |  |
| `max_new_tokens` | `int` | `512` |  |
| `temperature` | `float` | `0.8` |  |
| `top_p` | `float` | `0.95` |  |
| `seed` | `int \| None` | `None` |  |
| `thinking` | `bool \| str` | `'auto'` |  |
| `system_prompt` | `str \| None` | `None` |  |
| `private_context` | `tuple` | `()` |  |
| `tools` | `tuple` | `()` |  |
| `max_tool_iters` | `int` | `4` |  |
| `kv_reuse` | `bool \| str` | `'auto'` |  |
| `steering` | `object` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `MODEL_TYPES` | `frozenset[str]` |  |
| `adapter_path` | `str \| None` |  |
| `attn` | `str` |  |
| `device` | `str \| torch.device \| None` |  |
| `dtype` | `str` |  |
| `hf_id` | `str \| None` |  |
| `input_device` | `'torch.device'` | Where this participant's `input_ids` must land — the loaded model's **input-embedding** device. |
| `kv_reuse` | `bool \| str` |  |
| `max_new_tokens` | `int` |  |
| `max_tool_iters` | `int` |  |
| `model` | `'PreTrainedModel'` | The loaded HF model, loading it on first access (cached process-wide). |
| `name` | `str` |  |
| `private_context` | `tuple` |  |
| `quant` | `str \| None` |  |
| `revision` | `str \| None` |  |
| `seed` | `int \| None` |  |
| `steering` | `object` |  |
| `system_prompt` | `str \| None` |  |
| `temperature` | `float` |  |
| `thinking` | `bool \| str` |  |
| `tokenizer` | `'PreTrainedTokenizerBase'` | The loaded tokenizer, loading the model+tokenizer on first access (cached process-wide). |
| `tools` | `tuple` |  |
| `top_p` | `float` |  |
| `weights_path` | `str \| None` |  |

## Methods {#methods}

## `batch_signature` {#batch_signature}

```python
batch_signature(self) -> tuple
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L283-L291)

Key identifying which model this participant would batch AS (used by the co-stepper).

When loaded, the
cached model object's identity is authoritative; when not yet loaded, the load recipe is (the cache
guarantees same recipe on one device -> same object), so participants can be grouped WITHOUT forcing a
load.

## `for_model_type` {#for_model_type}

```python
for_model_type(cls, model_type: str | None) -> type['ModelParticipant']
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L159-L163)

The registered participant class for a transformers `config.model_type` (e.g. `qwen2`, `gemma2`), falling back to base `ModelParticipant` for any family that declares no specialized subclass.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model_type` | `str \| None` | *required* |  |

## `from_model` {#from_model}

```python
from_model(
	cls,
	model: PreTrainedModel,
	tokenizer: PreTrainedTokenizerBase | None = None,
	*,
	name: str,
	device: str | torch.device | None = None,
	**participant_kwargs={},
) -> Self
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L165-L190)

Build a participant of THIS class from an already-loaded `model` (the eager path — e.g. to wrap a model you already hold, or share weights between speakers).

`tokenizer` is optional — when omitted it is inferred
from `model.config._name_or_path`. The chat-template flags (`supports_system_role` /
`requires_alternating_roles`) are derived from the tokenizer's own template. `hf_id`/`dtype` are read
back from the model so the participant can still be pickled + re-loaded on a spawn worker. Because it
constructs `cls`, calling it on a subclass returns that subclass — use `AutoModelParticipant.from_model`
to have the family resolved from `config.model_type`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `PreTrainedModel` | *required* |  |
| `tokenizer` | `PreTrainedTokenizerBase \| None` | `None` |  |
| `name` | `str` | *required* |  |
| `device` | `str \| torch.device \| None` | `None` |  |
| `participant_kwargs` |  | `{}` |  |

## `from_pretrained` {#from_pretrained}

```python
from_pretrained(
	cls,
	id_or_path: str | Path,
	*,
	name: str,
	device: str | torch.device = 'cuda',
	load_kwargs: dict | None = None,
	**participant_kwargs={},
) -> Self
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L192-L207)

Build a participant of THIS class that will load `id_or_path` (an HF id or local path) **lazily on first use** — no weights are touched here.

`load_kwargs` (`dtype` / `attn` / `quant` / `revision` /
`weights_path` / `adapter_path`) are recorded for that deferred load; `participant_kwargs` (`temperature`,
`max_new_tokens`, `system_prompt`, `tools`, `kv_reuse`, …) go to the participant. When the load fires
it is process-cached, so all same-(id, device, dtype, …) participants share ONE model object. As with
`from_model`, the class is `cls` — use `AutoModelParticipant.from_pretrained` to resolve the family
from `config.model_type` (it reads only the config, still no weights).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `id_or_path` | `str \| Path` | *required* |  |
| `name` | `str` | *required* |  |
| `device` | `str \| torch.device` | `'cuda'` |  |
| `load_kwargs` | `dict \| None` | `None` |  |
| `participant_kwargs` |  | `{}` |  |

## `generate` {#generate}

```python
generate(
	self,
	view: list[dict],
	*,
	steering=None,
	capture=None,
	patch=None,
	return_logprobs: bool = False,
	turn: int | None = None,
	max_new_tokens: int | None = None,
	seat: str | None = None,
) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L327-L389)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `view` | `list[dict]` | *required* |  |
| `steering` |  | `None` |  |
| `capture` |  | `None` |  |
| `patch` |  | `None` |  |
| `return_logprobs` | `bool` | `False` |  |
| `turn` | `int \| None` | `None` |  |
| `max_new_tokens` | `int \| None` | `None` |  |
| `seat` | `str \| None` | `None` |  |

## `generate_batch` {#generate_batch}

```python
generate_batch(
	self,
	views: list[list[dict]],
	*,
	turn: int | None = None,
	group_seed: int | None = None,
	max_new_tokens: int | None = None,
) -> list[Message]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L453-L524)

Batched generation for many independent conversations that share THIS model (`throughput` mode).

Renders each `view` with this model's chat template and runs **one** `model.generate` over the
left-padded batch, returning one `Message` per view — the co-stepping throughput win (5-20x on a
rollout). `max_new_tokens` overrides this participant's per-turn cap for the batch (the co-stepper passes a
`turn_cap` here so a `TokenBudget` can shrink the final round). **No tools/steering/capture/logprobs**
here: callers needing those fall back to the per-conversation `generate`. Tokens are **not** guaranteed
identical to unbatched — batch composition and the single global RNG perturb rows (see PLAN §Execution
modes); only distributional reproducibility holds. `metadata['batched']` marks these turns;
`metadata['shared_prefill']` marks the fast path.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `views` | `list[list[dict]]` | *required* |  |
| `turn` | `int \| None` | `None` |  |
| `group_seed` | `int \| None` | `None` |  |
| `max_new_tokens` | `int \| None` | `None` |  |

## `generate_step` {#generate_step}

```python
generate_step(
	self,
	view: list[dict],
	*,
	tool_schemas: list[dict] | None = None,
	steering=None,
	capture=None,
	patch=None,
	return_logprobs: bool = False,
	turn: int | None = None,
	max_new_tokens: int | None = None,
	seat: str | None = None,
) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L391-L451)

Run one model generation without executing requested tools.

This is the policy/model boundary used by external agent runtimes such as Inspect and Control Tower:
`tool_schemas` are rendered by the participant's native chat template, parsed calls are returned as
serializable dictionaries in `Message.metadata["tool_calls"]`, and the caller remains responsible for
executing them. Keeping execution outside Interlens lets the outer runtime monitor, approve, replace, or
sandbox each action.

**Returns**

| Name | Type | Description |
|---|---|---|
|  | [Message](../../../message/Message.md) | A visible `Message` with usage/reasoning metadata and zero or more parsed `tool_calls`. Tools are never |
|  | [Message](../../../message/Message.md) | executed by this method. |

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `view` | `list[dict]` | *required* | Flattened chat history as dictionaries with `role` and `content`. Assistant tool calls and tool results may use the standard `tool_calls` / `tool_call_id` fields. |
| `tool_schemas` | `list[dict] \| None` | `None` | OpenAI-style function schemas available for this step. Pass `None` or `[]` to disable tool calling; use schemas when the outer runtime must execute and observe calls itself. |
| `steering` |  | `None` | Optional activation steering applied during this generation. `None` uses the participant's persistent `steering` setting. |
| `capture` |  | `None` | Optional activation-capture request for this generation. |
| `patch` |  | `None` | Optional activation patch applied during this generation. |
| `return_logprobs` | `bool` | `False` | Whether to record generated-token log probabilities in message metadata. |
| `turn` | `int \| None` | `None` | Optional turn index used to tag captured activations. |
| `max_new_tokens` | `int \| None` | `None` | Per-call output cap. `None` uses the participant's configured `max_new_tokens`. |
| `seat` | `str \| None` | `None` | Optional arena seat identifier, accepted for parity with :meth:`generate`; local participants do not otherwise use it. |

## `parse_tool_calls` {#parse_tool_calls}

```python
parse_tool_calls(self, text: str) -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L626-L640)

Parse tool calls out of a generation.

Base handles the common Hermes/Qwen `<tool_call>{json}</tool_call>`
format (JSON extraction via :func:`interlens.parsing.iter_tagged_json`); families with other formats
(Gemma's ```` ```tool_code ````, Llama's `<|python_tag|>`) override this. An unrecognized/absent call
yields `[]` so the loop treats the output as a final message.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |

## `render_tool_result` {#render_tool_result}

```python
render_tool_result(self, call, result) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L642-L645)

Render a tool result as the standard structured `tool` message; the tokenizer's own template turns it into the family-native format.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `call` |  | *required* |  |
| `result` |  | *required* |  |

## `split_reasoning` {#split_reasoning}

```python
split_reasoning(self, text: str) -> tuple[str, str | None]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/model_participant.py#L321-L325)

Split a raw completion into `(visible_content, parsed_think)`.

Base handles the leading
`<think>...</think>` convention (via :func:`interlens.parsing.split_leading_think`); families with
other delimiters override this.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
