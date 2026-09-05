# `ACConst`

AC_const(alpha): accept iff `incoming >= alpha` (eq. 4.6).

```python
ACConst(alpha: float = 0.7)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L269-L276)

**Inherits from:** [AcceptanceCondition](AcceptanceCondition.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `alpha` | `float` | `0.7` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `alpha` |  |  |

## Methods {#methods}

## `accepts` {#accepts}

```python
accepts(self, state, incoming, planned_next)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L275-L276)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` |  | *required* |  |
| `incoming` |  | *required* |  |
| `planned_next` |  | *required* |  |
