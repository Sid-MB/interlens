# `DeclaredGreedyHoldoutPolicy`

:class:`GreedyHoldoutPolicy` that ANNOUNCES its ultimatum on its first turn and then never speaks again.

```python
DeclaredGreedyHoldoutPolicy()
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L691-L704)

**Inherits from:** [GreedyHoldoutPolicy](GreedyHoldoutPolicy.md)

Behaviourally identical to the silent version — same proposals, same acceptance rule, same terminal vote —
so any difference in what the table does is attributable to the declaration alone. The capitulation prior
from the program's sycophancy work predicts the announcement makes LLM seats cave harder: a partner who
states an immovable position is exactly the pressure those models fold to.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |

## Methods {#methods}

## `declaration` {#declaration}

```python
declaration(self, state: NegotiationState) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L701-L704)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
