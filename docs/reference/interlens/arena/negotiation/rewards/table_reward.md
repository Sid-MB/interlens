# `table_reward`

Table-welfare term `R_table = mean_i g(z_i)` on a closed deal, the smoothed log form of normalized Nash welfare.

```python
table_reward(
	z: Sequence[float] | None,
	*,
	n_agents: int | None = None,
	eps: float = DEFAULT_EPS,
	g_floor: float | None = None,
) -> float
```

Defined in [`interlens.arena.negotiation.rewards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/rewards.py#L101-L114)

`z=None` means no deal and returns `no_deal_utility` (`n_agents` is then unused — the mean of a
constant is that constant). `g_floor` clips each party's term from below; see
:func:`smoothed_log_utility`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z` | `Sequence[float] \| None` | *required* |  |
| `n_agents` | `int \| None` | `None` |  |
| `eps` | `float` | `DEFAULT_EPS` |  |
| `g_floor` | `float \| None` | `None` |  |
