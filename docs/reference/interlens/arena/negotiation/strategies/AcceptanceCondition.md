# `AcceptanceCondition`

Decide whether to accept the standing offer given the agent's own utility of it (`incoming`) and of the deal it is about to propose (`planned_next`), both on the normalized `[0, 1]` scale.

```python
AcceptanceCondition()
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L249-L255)

**Inherits from:** `ABC`

## Methods {#methods}

## `accepts` {#accepts}

```python
accepts(self, state: NegotiationState, incoming: float, planned_next: float) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L253-L255)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
| `incoming` | `float` | *required* |  |
| `planned_next` | `float` | *required* |  |
