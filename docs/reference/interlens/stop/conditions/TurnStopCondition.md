# `TurnStopCondition`

Stop after `max_turns` committed turns.

```python
TurnStopCondition(max_turns: int)
```

Defined in [`interlens.stop.conditions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L32-L44)

**Inherits from:** [StopCondition](../stop_condition/StopCondition.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `max_turns` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `count` |  |  |
| `max_turns` |  |  |

## Methods {#methods}

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L43-L44)

## `should_stop` {#should_stop}

```python
should_stop(self, conversation: 'Conversation', last_message: 'Message') -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L39-L41)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `last_message` | `'Message'` | *required* |  |
