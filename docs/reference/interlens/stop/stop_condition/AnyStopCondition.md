# `AnyStopCondition`

Fires when *any* member condition fires.

```python
AnyStopCondition(conditions: list[StopCondition])
```

Defined in [`interlens.stop.stop_condition`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/stop_condition.py#L71-L88)

**Inherits from:** [StopCondition](StopCondition.md)

`run(until=[...])` wraps a list in this.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conditions` | list[[StopCondition](StopCondition.md)] | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `conditions` |  |  |

## Methods {#methods}

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/stop_condition.py#L86-L88)

## `should_stop` {#should_stop}

```python
should_stop(self, conversation: 'Conversation', last_message: 'Message') -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/stop_condition.py#L77-L79)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `last_message` | `'Message'` | *required* |  |

## `turn_cap` {#turn_cap}

```python
turn_cap(self, conversation: 'Conversation') -> int | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/stop_condition.py#L81-L84)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
