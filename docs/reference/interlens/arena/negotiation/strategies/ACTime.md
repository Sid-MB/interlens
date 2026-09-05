# `ACTime`

AC_time(T): accept anything once the time fraction reaches `t_frac` (eq. 4.7).

```python
ACTime(t_frac: float = 0.9)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L279-L286)

**Inherits from:** [AcceptanceCondition](AcceptanceCondition.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `t_frac` | `float` | `0.9` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `t_frac` |  |  |

## Methods {#methods}

## `accepts` {#accepts}

```python
accepts(self, state, incoming, planned_next)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L285-L286)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` |  | *required* |  |
| `incoming` |  | *required* |  |
| `planned_next` |  | *required* |  |
