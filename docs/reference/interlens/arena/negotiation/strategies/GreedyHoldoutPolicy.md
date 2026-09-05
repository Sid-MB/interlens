# `GreedyHoldoutPolicy`

Take it or leave it: proposes its own-max deal exactly as :class:`GreedyAnchorPolicy` does, but accepts ONLY that deal — every other offer is declined, including offers that are individually rational for it.

```python
GreedyHoldoutPolicy()
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L645-L673)

**Inherits from:** [GreedyAnchorPolicy](GreedyAnchorPolicy.md)

This is the one policy here that is not individually rational in the game-theoretic sense: it walks away
from free surplus, so it should cost itself deals. It is the extraction upper bound — the test of whether
an agreeable LLM table simply capitulates to a seat that never moves. On the terminal forced vote it
applies the same rule rather than the base class's accept-anything-positive vote, which is the whole
point: the ordinary rational agent's last-round logic (any deal beats no deal) is exactly what this policy
refuses.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L661-L667)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |

## `vote` {#vote}

```python
vote(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L669-L673)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
