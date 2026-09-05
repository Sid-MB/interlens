# `DemandFractionPolicy`

Declare a demand LEVEL and hold to it: accept any package worth at least `accept_frac` of this seat's own MAXIMUM achievable score, propose its own best deal, and announce the numeric rule up front.

```python
DemandFractionPolicy(*, accept_frac: float = 0.9, name: str | None = None)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L707-L765)

**Inherits from:** [GreedyAnchorPolicy](GreedyAnchorPolicy.md)

The bar is a fraction of the everything-goes-my-way total, not of the reservation value — so at the
default 0.9 the policy is asking for nine tenths of the best it could conceivably do, while still leaving
a visible margin for the other parties to work in. It is the middle rung between
:class:`GreedyAnchorPolicy` (signs anything above its threshold) and :class:`GreedyHoldoutPolicy` (signs
only its maximum): a commitment WITH a margin, testing whether a slightly softer ultimatum extracts nearly
as much while keeping deals alive.

The declared number is this seat's own private score information, voluntarily disclosed. That is
deliberate and is the mechanism under test — a commitment is only credible if the counterparty can check
an offer against it — but it does mean this policy is not information-symmetric with the others, and a
private-information game is no longer fully private on this seat once it speaks.

Parameters
----------
accept_frac : float
    Fraction of the own-maximum score demanded, in `(0, 1]`. 1.0 degenerates to holdout-by-value.
name : str
    Display name.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `accept_frac` | `float` | `0.9` |  |
| `name` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `accept_frac` |  |  |
| `name` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L745-L751)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |

## `declaration` {#declaration}

```python
declaration(self, state: NegotiationState) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L760-L765)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |

## `vote` {#vote}

```python
vote(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L753-L758)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |
