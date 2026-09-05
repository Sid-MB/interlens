# `shaping_reward`

Potential-based shaping increment `gamma * Phi(s') - Phi(s)` for one turn: "did your move pull the standing offer toward or away from a fair deal?".

```python
shaping_reward(
	z_before: Sequence[float] | None,
	z_after: Sequence[float] | None,
	*,
	gamma: float = 1.0,
	eps: float = DEFAULT_EPS,
	g_floor: float | None = None,
) -> float
```

Defined in [`interlens.arena.negotiation.rewards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/rewards.py#L180-L188)

Potential-based shaping provably preserves the optimal
policy (Ng, Harada & Russell 1999), so this densifies credit assignment over a ~25-round episode without
changing what is being optimized. `gamma` should match the discount used by the learner (`1.0` for the
undiscounted episodic setting).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z_before` | `Sequence[float] \| None` | *required* |  |
| `z_after` | `Sequence[float] \| None` | *required* |  |
| `gamma` | `float` | `1.0` |  |
| `eps` | `float` | `DEFAULT_EPS` |  |
| `g_floor` | `float \| None` | `None` |  |
