# `NaiveTitForTatPolicy`

Behavior-dependent tit-for-tat (Faratin §3.3): mirror the opponent's most recent concession (measured in this agent's own normalized utility) as an equal concession from the agent's last demand; start near the own optimum.

```python
NaiveTitForTatPolicy(
	*,
	acceptance: AcceptanceCondition | None = None,
	name: str = 'naive-tft',
)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L519-L546)

**Inherits from:** [Policy](Policy.md)

Accept per `acceptance`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `acceptance` | [AcceptanceCondition](AcceptanceCondition.md) \| None | `None` |  |
| `name` | `str` | `'naive-tft'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `acceptance` |  |  |
| `name` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L529-L546)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
