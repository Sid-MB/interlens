# `ACNext`

AC_next(alpha, beta): accept iff `alpha * incoming + beta >= planned_next` — the incoming bid is at least as good as what you were about to send (Baarslag eq. 4.4; alpha=1, beta=0 standard).

```python
ACNext(alpha: float = 1.0, beta: float = 0.0)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L258-L266)

**Inherits from:** [AcceptanceCondition](AcceptanceCondition.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `alpha` | `float` | `1.0` |  |
| `beta` | `float` | `0.0` |  |

## Methods {#methods}

## `accepts` {#accepts}

```python
accepts(self, state, incoming, planned_next)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L265-L266)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` |  | *required* |  |
| `incoming` |  | *required* |  |
| `planned_next` |  | *required* |  |
