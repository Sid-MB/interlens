# `ElapsedTimeStopCondition`

Stop once `seconds` of wall-clock have elapsed since the run started (monotonic clock).

```python
ElapsedTimeStopCondition(seconds: float)
```

Defined in [`interlens.stop.conditions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L66-L79)

**Inherits from:** [StopCondition](../stop_condition/StopCondition.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seconds` | `float` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `seconds` |  |  |
| `start` |  |  |

## Methods {#methods}

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L78-L79)

## `should_stop` {#should_stop}

```python
should_stop(self, conversation: 'Conversation', last_message: 'Message') -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L73-L76)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `last_message` | `'Message'` | *required* |  |
