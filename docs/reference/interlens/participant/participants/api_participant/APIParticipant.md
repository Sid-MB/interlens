# `APIParticipant`

A participant backed by a hosted API — Claude via `anthropic` (`provider="anthropic"`, the default) or any model behind OpenRouter (`provider="openrouter"`, OpenAI-compatible) — for use as a debate opponent, moderator, or the classifier inside an `analyze` callback.

```python
APIParticipant(
	name: str = '',
	model_id: str = '',
	provider: Provider = 'anthropic',
	system_prompt: str | None = None,
	private_context: tuple = (),
	max_tokens: int = 512,
	temperature: float = 1.0,
	batch: bool = False,
	client: object = None,
	openrouter_routing: OpenRouterRouting | None = None,
	prompt_cache: PromptCache | None = None,
	meter: object = None,
	turn_token_floor: int | None = None,
	thinking: object = None,
	effort: str | None = None,
	requires_alternating_roles: bool = True,
)
```

Defined in [`interlens.participant.participants.api_participant`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L183-L502)

**Inherits from:** [Functional](../../../functional/Functional.md), [Participant](../../participant/Participant.md)

It is a full participant for *conversation* purposes but has **no local model** — so there is no device,
no activations, and no steering. Any interp request (`capture`/`steering`/`patch`/`return_logprobs`)
**raises** rather than silently no-op'ing: in a measurement harness, a steering sweep that quietly did
nothing on an API participant would produce a false "no effect" conclusion. Seeds don't bind hosted models,
so API turns are excluded from the identical-replay guarantee.

Concurrency is network-bound, so pure-API conversations run thread-pooled rather than process-per-GPU
(handled by the runner). The `client` callable is injectable for testing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | `''` |  |
| `model_id` | `str` | `''` |  |
| `provider` | `Provider` | `'anthropic'` |  |
| `system_prompt` | `str \| None` | `None` |  |
| `private_context` | `tuple` | `()` |  |
| `max_tokens` | `int` | `512` |  |
| `temperature` | `float` | `1.0` |  |
| `batch` | `bool` | `False` |  |
| `client` | `object` | `None` |  |
| `openrouter_routing` | [OpenRouterRouting](OpenRouterRouting.md) \| None | `None` |  |
| `prompt_cache` | [PromptCache](PromptCache.md) \| None | `None` |  |
| `meter` | `object` | `None` |  |
| `turn_token_floor` | `int \| None` | `None` |  |
| `thinking` | `object` | `None` |  |
| `effort` | `str \| None` | `None` |  |
| `requires_alternating_roles` | `bool` | `True` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `batch` | `bool` |  |
| `client` | `object` |  |
| `effort` | `str \| None` | Reasoning-effort level, Anthropic only: `"low"`/`"medium"`/`"high"`/`"xhigh"`/`"max"`, sent as `output_config={"effort": ...}`. |
| `max_tokens` | `int` |  |
| `meter` | `object` | Optional `interlens.usage.UsageMeter`: every call this participant makes is reported into it (tokens, dollars at the actual billing multiplier — batch-served turns bill at 0.5× — and refusal counts), so one shared meter across participants gives a live, run-level spend ledger with reservation gating. |
| `model_id` | `str` |  |
| `name` | `str` |  |
| `openrouter_routing` | [OpenRouterRouting](OpenRouterRouting.md) \| None | Required for `provider="openrouter"`. |
| `private_context` | `tuple` |  |
| `prompt_cache` | [PromptCache](PromptCache.md) \| None | Where to place Anthropic `cache_control` breakpoints, or `None` (default) for no caching. |
| `provider` | `Provider` |  |
| `requires_alternating_roles` | `bool` |  |
| `system_prompt` | `str \| None` |  |
| `temperature` | `float` |  |
| `thinking` | `object` | Reasoning control, Anthropic only: `None` keeps the model's default (adaptive thinking on current Claude models — which spends from `max_tokens`), `"disabled"` turns thinking off, an `int` sets an explicit thinking budget, and a dict passes through verbatim. |
| `turn_token_floor` | `int \| None` | Thinking-aware lower bound on an externally imposed per-turn cap. |

## Methods {#methods}

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L285-L304)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L306-L342)

Generate one turn for many independent conversations at once — the API analogue of `ModelParticipant.generate_batch`, driven by the runner's co-stepper (`rollout(..., batched=True)`) to make large API rollouts cheap and throughput-bound.

With `batch=True` every view is sent as one **asynchronous provider batch** (Anthropic Message Batches /
OpenAI Batch API) via `client.submit_batch` — ~50% cost and much higher throughput, at the price of
batch-window latency. **If the provider has no batch API (e.g. OpenRouter) this raises** rather than
silently degrading, so a requested batch is never quietly run as serial calls. With `batch=False` it
falls back to sequential per-view calls (correct, just no batch discount). Interp is unavailable here, as
for `generate`. `turn`/`group_seed` are accepted for co-stepper compatibility but unused (seeds do
not bind hosted models). `metadata['batched']` marks these turns.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `views` | `list[list[dict]]` | *required* |  |
| `turn` | `int \| None` | `None` |  |
| `group_seed` | `int \| None` | `None` |  |
| `max_new_tokens` | `int \| None` | `None` |  |

## `request_config` {#request_config}

```python
request_config(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_participant.py#L391-L403)

The reasoning-relevant request parameters this participant will actually send.

Exists so a run manifest can record the condition it ran rather than the condition it *meant* to run:
`thinking=None` and an explicit adaptive dict produce identical behaviour on current Claude models but
are not the same record, and a cell labelled "thinking on" is uninterpretable without knowing which one
it sent.
