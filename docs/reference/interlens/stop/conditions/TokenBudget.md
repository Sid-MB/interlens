# `TokenBudget`

A per-conversation compute budget — the matched-compute primitive for fair solo-vs-pair comparisons.

```python
TokenBudget(per_conversation: int | None = None, per_turn: int | None = None)
```

Defined in [`interlens.stop.conditions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L99-L130)

**Inherits from:** [StopCondition](../stop_condition/StopCondition.md)

`per_conversation` stops a conversation once ITS OWN cumulative generated tokens reach the budget, and
`per_turn` caps each individual turn so the allowance is spread across real conversation turns rather than
consumed by one monologue. Both are enforced via `turn_cap` too: the run loop shrinks the next generation to
`min(speaker cap, per_turn, per_conversation - spent)`, so the budget is respected without overshoot.

**The budget is per-conversation, not a shared pool.** Spend is read from the conversation's own transcript
(`metadata['n_tokens']`), so the condition is stateless — in a rollout of N copies, each copy independently
gets the full budget. Cheap to count (never re-tokenizes) and trivially picklable, so it works installed
directly (`run_until=TokenBudget(...)`) or ambiently (`with TokenBudget(per_conversation=200): conv.rollout()`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `per_conversation` | `int \| None` | `None` |  |
| `per_turn` | `int \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `per_conversation` |  |  |
| `per_turn` |  |  |

## Methods {#methods}

## `should_stop` {#should_stop}

```python
should_stop(self, conversation: 'Conversation', last_message: 'Message') -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L119-L122)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `last_message` | `'Message'` | *required* |  |

## `turn_cap` {#turn_cap}

```python
turn_cap(self, conversation: 'Conversation') -> int | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/stop/conditions.py#L124-L130)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
