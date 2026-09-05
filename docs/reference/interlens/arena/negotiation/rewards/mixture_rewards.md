# `mixture_rewards`

Per-seat episode rewards `R_i(lam) = (1 - lam) * g(z_i) + lam * R_table`, one per party in seat order.

```python
mixture_rewards(
	z: Sequence[float] | None,
	*,
	lam: float,
	n_agents: int | None = None,
	eps: float = DEFAULT_EPS,
	g_floor: float | None = None,
) -> list[float]
```

Defined in [`interlens.arena.negotiation.rewards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/rewards.py#L140-L158)

`lam=0` is pure self-interest (the manipulation check: it should reproduce the observed pathologies),
`lam=1` is pure table welfare (identical for every seat), and intermediate values trace the frontier
between them. On a no-deal episode (`z=None`) every seat gets `no_deal_utility` at any `lam`, so
`n_agents` is required to size the output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z` | `Sequence[float] \| None` | *required* |  |
| `lam` | `float` | *required* |  |
| `n_agents` | `int \| None` | `None` |  |
| `eps` | `float` | `DEFAULT_EPS` |  |
| `g_floor` | `float \| None` | `None` |  |
