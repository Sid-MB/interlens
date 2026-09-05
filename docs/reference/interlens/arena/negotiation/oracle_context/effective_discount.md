# `effective_discount`

The per-round continuation factor the acceptance/best-response/equilibrium oracles should use, read from the game as the single source of truth: `discount * (1 - breakdown_risk)` (time preference times the per-round no-breakdown survival probability — the BRW 1986 breakdown model).

```python
effective_discount(game, override=None) -> float
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L282-L294)

An explicit `override`
(a non-None oracle-level `discount`) wins, so a caller can still force a value; otherwise the game's own
impatience is honored. `GameSpec` defaults `discount=1.0` (neutral) / `breakdown_risk=0.0`, which
yields the Sandholm-Vulkan brinkmanship baseline — set `discount < 1` on the game for interior
concession to be rational.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `override` |  | `None` |  |
