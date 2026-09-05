# `violation_decomposition`

Split `table_reward` into `(among_ir, violation)` with `among_ir + violation == table_reward(z)`.

```python
violation_decomposition(
	z: Sequence[float] | None,
	*,
	eps: float = DEFAULT_EPS,
	g_floor: float | None = None,
) -> tuple[float, float]
```

Defined in [`interlens.arena.negotiation.rewards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/rewards.py#L117-L137)

`among_ir = mean_i g(max(z_i, eps))` is what the table would score if every shorted party were pinned at
its own threshold — the pure *distribution* term, which varies only with how well the surplus is divided
among parties that cleared their walk-away. `violation = mean_i [g(z_i) - g(max(z_i, eps))] <= 0` is the
penalty for shorting parties, and is exactly zero on an individually rational deal.

The split exists to be *measured*: taking the variance of each component over a campaign answers "how much of
the reward's dynamic range is the violation branch", which is the diagnosis of the v1 fairness-GRPO negative
(the objective was nominally Nash welfare but behaviourally an IR-violation penalty) and the calibration
target for `g_floor`. A no-deal episode is not a violation: it returns `(no_deal_utility, 0.0)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z` | `Sequence[float] \| None` | *required* |  |
| `eps` | `float` | `DEFAULT_EPS` |  |
| `g_floor` | `float \| None` | `None` |  |
