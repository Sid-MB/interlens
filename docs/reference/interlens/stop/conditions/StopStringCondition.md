# `StopStringCondition`

Stop when a committed message's visible `content` contains any of the given strings (a done-signal).

```python
StopStringCondition(strings)
```

Defined in [`interlens.stop.conditions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L82-L89)

**Inherits from:** [StopCondition](../stop_condition/StopCondition.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `strings` |  | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `strings` |  |  |

## Methods {#methods}

## `should_stop` {#should_stop}

```python
should_stop(self, conversation: 'Conversation', last_message: 'Message') -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L88-L89)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `last_message` | `'Message'` | *required* |  |
