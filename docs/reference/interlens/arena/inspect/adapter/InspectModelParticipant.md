# `InspectModelParticipant`

An interlens `Participant` played by an Inspect model.

```python
InspectModelParticipant(
	name: str,
	model=None,
	*,
	loop=None,
	meter: UsageMeter | None = None,
	max_tokens: int = 2048,
	system_prompt: str | None = None,
)
```

Defined in [`interlens.arena.inspect.adapter`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/inspect/adapter.py#L58-L116)

**Inherits from:** [Participant](../../../participant/participant/Participant.md)

`generate` runs in a worker thread (that is how the engine and `Conversation` drive blocking
participants), so it posts the async `model.generate` back onto the solver's event loop and blocks on
the future — Inspect's connection limits and retries apply as usual. Usage telemetry lands in
`Message.metadata` under the same keys every other participant uses, so budgets, metering, and episode
accounting work unchanged.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `model` |  | `None` |  |
| `loop` |  | `None` |  |
| `meter` | [UsageMeter](../../../usage/UsageMeter.md) \| None | `None` |  |
| `max_tokens` | `int` | `2048` |  |
| `system_prompt` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `loop` |  |  |
| `max_tokens` |  |  |
| `meter` |  |  |
| `model` |  |  |
| `model_id` |  |  |
| `name` |  |  |
| `private_context` |  |  |
| `requires_alternating_roles` |  |  |
| `system_prompt` |  |  |

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/inspect/adapter.py#L82-L116)

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
