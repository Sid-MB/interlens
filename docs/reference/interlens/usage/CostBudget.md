# `CostBudget`

A per-conversation **dollar** budget — the cost-denominated sibling of `TokenBudget`.

```python
CostBudget(per_conversation: float)
```

Defined in [`interlens.usage`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L278-L292)

**Inherits from:** [StopCondition](../stop/stop_condition/StopCondition.md)

Stops a conversation once its own cumulative recorded turn cost (`metadata['cost_usd']`, written by
metered `APIParticipant`s) reaches `per_conversation` dollars. Stateless like `TokenBudget` (spend is
re-read from the transcript), so it works installed directly or ambiently and each rollout copy
independently gets the full budget. Turns without a cost record (local models, scripted participants)
contribute $0 — this budget only constrains metered hosted-API spend.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `per_conversation` | `float` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `per_conversation` |  |  |

## Methods {#methods}

## `should_stop` {#should_stop}

```python
should_stop(self, conversation: 'Conversation', last_message: 'Message') -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L290-L292)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `last_message` | `'Message'` | *required* |  |
