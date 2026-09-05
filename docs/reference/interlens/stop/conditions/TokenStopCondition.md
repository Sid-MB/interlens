# `TokenStopCondition`

Stop once the total generated tokens across turns reach `max_tokens`.

```python
TokenStopCondition(max_tokens: int)
```

Defined in [`interlens.stop.conditions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L47-L63)

**Inherits from:** [StopCondition](../stop_condition/StopCondition.md)

The per-turn count comes from `Message.metadata['n_tokens']`, which `ModelParticipant.generate` records —
so the source of truth is defined, not guessed. Turns without a count (e.g. seeded messages) contribute 0.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `max_tokens` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `max_tokens` |  |  |
| `total` |  |  |

## Methods {#methods}

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L62-L63)

## `should_stop` {#should_stop}

```python
should_stop(self, conversation: 'Conversation', last_message: 'Message') -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L58-L60)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `last_message` | `'Message'` | *required* |  |
