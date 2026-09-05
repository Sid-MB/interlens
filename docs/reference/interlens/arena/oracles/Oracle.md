# `Oracle`

A rational reference policy that scores a seat's options at a decision point.

```python
Oracle()
```

Defined in [`interlens.arena.oracles`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L165-L181)

**Inherits from:** `ABC`

Subclasses implement :meth:`evaluate`. The arguments are deliberately generic so the ABC carries no
negotiation specifics:

- `game` — the game definition (the negotiation `GameSpec`: deal space, score sheets, thresholds).
- `history` — the sequence of prior turns/actions the oracle may condition on.
- `agent` — the seat being evaluated (its private info defines its value function).
- `legal` — the legal actions available to `agent` now (the keys the verdict scores).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` | `str` |  |

## Methods {#methods}

## `evaluate` {#evaluate}

```python
evaluate(self, game: Any, history: Sequence, agent: str, legal: Sequence) -> OracleVerdict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L179-L181)

Return an :class:`OracleVerdict` scoring `legal` for `agent` given `game` and `history`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | `Any` | *required* |  |
| `history` | `Sequence` | *required* |  |
| `agent` | `str` | *required* |  |
| `legal` | `Sequence` | *required* |  |
