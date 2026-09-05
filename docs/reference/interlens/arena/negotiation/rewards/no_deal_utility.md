# `no_deal_utility`

The utility every seat receives when the episode ends with no deal: `g(0) = log(eps) - 1` (`-5.605` at the default `eps`).

```python
no_deal_utility(*, eps: float = DEFAULT_EPS, g_floor: float | None = None) -> float
```

Defined in [`interlens.arena.negotiation.rewards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/rewards.py#L92-L98)

Sits strictly below any weakly-IR deal (`z >= 0` scores `>= g(0)`)
and strictly above deals that push a party below `z = 0`. `g_floor` is accepted (and validated) for
signature symmetry with the rest of the module but cannot change this value, since a legal floor is by
definition below it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `eps` | `float` | `DEFAULT_EPS` |  |
| `g_floor` | `float \| None` | `None` |  |
