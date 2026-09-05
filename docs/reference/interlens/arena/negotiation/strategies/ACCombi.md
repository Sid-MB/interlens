# `ACCombi`

AC_combi(T, alpha): `AC_next OR (AC_time(T) AND incoming >= alpha)` (eq. 4.8; combi variants empirically dominate).

```python
ACCombi(t_frac: float = 0.9, alpha: float = 0.6, next_alpha: float = 1.0)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L289-L300)

**Inherits from:** [AcceptanceCondition](AcceptanceCondition.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `t_frac` | `float` | `0.9` |  |
| `alpha` | `float` | `0.6` |  |
| `next_alpha` | `float` | `1.0` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `alpha` |  |  |
| `next` |  |  |
| `time` |  |  |

## Methods {#methods}

## `accepts` {#accepts}

```python
accepts(self, state, incoming, planned_next)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L298-L300)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` |  | *required* |  |
| `incoming` |  | *required* |  |
| `planned_next` |  | *required* |  |
