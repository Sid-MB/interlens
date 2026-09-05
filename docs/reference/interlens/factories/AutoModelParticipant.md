# `AutoModelParticipant`

Resolver for creating `Participant` instances automatically from HuggingFace model identifiers, local model paths, or already-loaded `PreTrainedModel`s.

```python
AutoModelParticipant()
```

Defined in [`interlens.factories`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/factories.py#L35-L100)

HF-style factory for family-correct local-model participants — the participant analog of
`AutoModelForCausalLM`. It resolves the concrete `ModelParticipant` subclass from the model's transformers
`config.model_type` via the class self-registry (`ModelParticipant.for_model_type`), then delegates the
actual build to that class's `from_model` / `from_pretrained` — so all the loading / tokenizer-inference /
chat-flag logic lives in one place (on `ModelParticipant`) and this class is *only* the family dispatcher.

- `from_` dispatches on the argument type (str id → `from_pretrained`; `PreTrainedModel` → `from_model`).
- To get a statically-known subclass, name it directly: `QwenModelParticipant.from_pretrained(...)`. This
  factory returns the (dynamically resolved) base `ModelParticipant` type.

## Methods {#methods}

## `from_` {#from_}

```python
from_(
	model: ModelLike,
	*,
	name: str,
	tokenizer: PreTrainedTokenizerBase | None = None,
	device: str | torch.device = 'cuda',
	load_kwargs: dict | None = None,
	**participant_kwargs: Any = {},
) -> ModelParticipant
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/factories.py#L50-L60)

Build a participant from either an HF id (str) or an already-loaded `PreTrainedModel`, dispatching to `from_pretrained` / `from_model`.

`tokenizer` applies only to the loaded-model case (an id / path loads
its own matching tokenizer, so it is ignored there).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `ModelLike` | *required* |  |
| `name` | `str` | *required* |  |
| `tokenizer` | `PreTrainedTokenizerBase \| None` | `None` |  |
| `device` | `str \| torch.device` | `'cuda'` |  |
| `load_kwargs` | `dict \| None` | `None` |  |
| `participant_kwargs` | `Any` | `{}` |  |

## `from_model` {#from_model}

```python
from_model(
	model: PreTrainedModel,
	tokenizer: PreTrainedTokenizerBase | None = None,
	*,
	name: str,
	device: str | torch.device | None = None,
	**participant_kwargs: Any = {},
) -> ModelParticipant
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/factories.py#L93-L100)

Build a family-correct participant from an already-loaded `model` — the class is resolved from `config.model_type` (unknown types fall back to base `ModelParticipant`), then that class's :meth:`ModelParticipant.from_model` does the tokenizer inference and chat-flag derivation.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `PreTrainedModel` | *required* |  |
| `tokenizer` | `PreTrainedTokenizerBase \| None` | `None` |  |
| `name` | `str` | *required* |  |
| `device` | `str \| torch.device \| None` | `None` |  |
| `participant_kwargs` | `Any` | `{}` |  |

## `from_pretrained` {#from_pretrained}

```python
from_pretrained(
	id_or_path: str | Path,
	*,
	name: str,
	device: str | torch.device = 'cuda',
	load_kwargs: dict | None = None,
	**participant_kwargs: Any = {},
) -> ModelParticipant
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/factories.py#L62-L91)

Return a family-correct participant for `id_or_path` (an HF id or local path) that will load its weights **lazily on first use**.

The concrete class is resolved from `config.model_type` by reading ONLY the
model's config (`AutoConfig.from_pretrained` — cheap, no weights); `load_kwargs` (`dtype` / `attn` /
`quant` / `revision` / `weights_path`) are recorded for that deferred load and `participant_kwargs`
go to the participant (see :meth:`ModelParticipant.from_pretrained`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `id_or_path` | `str \| Path` | *required* |  |
| `name` | `str` | *required* |  |
| `device` | `str \| torch.device` | `'cuda'` |  |
| `load_kwargs` | `dict \| None` | `None` |  |
| `participant_kwargs` | `Any` | `{}` |  |
