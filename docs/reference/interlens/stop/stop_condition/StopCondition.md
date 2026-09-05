# `StopCondition`

A stateful predicate that ends a `Conversation.run` early.

```python
StopCondition()
```

Defined in [`interlens.stop.stop_condition`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/stop_condition.py#L37-L68)

**Inherits from:** `ABC`

Each condition is **stateful** (tracks its own counters) and is checked after every committed turn via
`should_stop(conversation, last_message)`. `reset()` clears state and is called at the start of each
`run` (and branches get fresh copies), so one instance can be reused across runs without leaking state.

A condition may also **cap the next generation** via `turn_cap` (e.g. a token budget shrinks the last turn so
it lands exactly on budget) and may be installed **ambiently** as a context manager (`with TokenBudget(...):
conv.rollout(...)` applies it to every conversation in the block). New conditions subclass this without any
change to `run`.

## Methods {#methods}

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/stop_condition.py#L54-L55)

Clear any accumulated state.

Default no-op for stateless conditions.

## `should_stop` {#should_stop}

```python
should_stop(self, conversation: 'Conversation', last_message: 'Message') -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/stop_condition.py#L50-L52)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `last_message` | `'Message'` | *required* |  |

## `turn_cap` {#turn_cap}

```python
turn_cap(self, conversation: 'Conversation') -> int | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/stop_condition.py#L57-L61)

An upper bound on the NEXT turn's generated tokens, or `None` for no cap.

The run loop passes it as
`max_new_tokens` (bounded by the speaker's own cap), so a budget condition can prevent both overshoot and a
single turn from consuming the whole allowance. Default: no cap.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
