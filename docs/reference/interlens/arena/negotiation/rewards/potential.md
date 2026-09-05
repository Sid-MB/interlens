# `potential`

Shaping potential `Phi(s) = max(R_table(standing offer at s), g(0))` — how good the table is right now.

```python
potential(
	z: Sequence[float] | None,
	*,
	eps: float = DEFAULT_EPS,
	g_floor: float | None = None,
) -> float
```

Defined in [`interlens.arena.negotiation.rewards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/rewards.py#L162-L177)

With no standing offer this is `no_deal_utility`, so the first offer is credited by how much better than
walking it is.

The floor at `g(0)` is what makes this usable as a shaping term. `table_reward` is unbounded below (the
linear branch is deliberately so, to keep gradient on threshold violations), so an absurd proposal could
otherwise drive `Phi` to -100 and produce a shaping increment an order of magnitude larger than the
episode reward it is supposed to densify. Flooring is not a fudge: a standing offer worse than no agreement
is worth no more than no agreement, because any party can simply refuse it. `Phi` is still a pure function
of the state, so potential-based shaping's policy-invariance guarantee is untouched, and the increment is now
bounded by `|g(0)|`. `g_floor` (see :func:`smoothed_log_utility`) additionally bounds each party's term
before the mean is taken; with a floor in play this `max` is rarely the binding constraint, but it is kept
so `Phi` has the same meaning under both reward shapes.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z` | `Sequence[float] \| None` | *required* |  |
| `eps` | `float` | `DEFAULT_EPS` |  |
| `g_floor` | `float \| None` | `None` |  |
