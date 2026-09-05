# `TimeDependentPolicy`

Faratin time-dependent tactic: concede own utility along `alpha(t) = k + (1 - k) (t/T)^{1/beta}` toward the reservation, propose the least-concession IR deal at/above the current target, and accept per `acceptance`.

```python
TimeDependentPolicy(
	beta: float,
	*,
	k: float = 0.0,
	acceptance: AcceptanceCondition | None = None,
	name: str | None = None,
)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L411-L466)

**Inherits from:** [Policy](Policy.md)

Parameters
----------
beta : float
    Concession exponent. `beta < 1` = Boulware (concede near deadline); `beta > 1` = Conceder;
    `beta = 1` linear.
k : float
    First-offer concession constant in `[0, 1]` (0 = open at the own optimum).
acceptance : AcceptanceCondition
    Acceptance rule (default AC_next).
name : str
    Display name.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `beta` | `float` | *required* |  |
| `k` | `float` | `0.0` |  |
| `acceptance` | [AcceptanceCondition](AcceptanceCondition.md) \| None | `None` |  |
| `name` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `acceptance` |  |  |
| `beta` |  |  |
| `k` |  |  |
| `name` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L460-L466)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |

## `boulware` {#boulware}

```python
boulware(cls, beta: float = 0.2, **kw={})
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L438-L441)

A Boulware agent (`beta < 1`; default 0.2).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `beta` | `float` | `0.2` |  |
| `kw` |  | `{}` |  |

## `conceder` {#conceder}

```python
conceder(cls, beta: float = 5.0, **kw={})
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L443-L446)

A Conceder agent (`beta > 1`; default 5.0).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `beta` | `float` | `5.0` |  |
| `kw` |  | `{}` |  |

## `concession` {#concession}

```python
concession(self, t: float) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L448-L452)

The Faratin concession level `alpha(t) = k + (1 - k) t^{1/beta}` at time fraction `t` in `[0, 1]` (0 = demand the optimum, 1 = conceded to the reservation).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `t` | `float` | *required* |  |

## `target_norm` {#target_norm}

```python
target_norm(self, state) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L454-L458)

The normalized own-utility level to demand now: `1 - concession(t) * (1 - reserve)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` |  | *required* |  |
