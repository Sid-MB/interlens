# `nearest_type_index`

The grid type closest to a true `(utility, threshold)` pair, and its distance.

```python
nearest_type_index(
	belief: BeliefState,
	deals_arr: np.ndarray,
	utility: np.ndarray,
	threshold: float,
) -> tuple[int, float]
```

Defined in [`interlens.arena.negotiation.belief_accuracy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/belief_accuracy.py#L107-L123)

Distance is `rmse(type utility, true utility) + |type tau - true tau|`: agreement of the whole utility
FUNCTION across every deal (not of a parameterization, which the grid samples only coarsely) plus
agreement of the reservation, both already on the same `[0, 1]` scale so they add without a weight to
argue about. A sheet that lies exactly on the grid scores 0.0 and therefore maps to itself, which is the
property that makes `posterior_mass_true_type` mean what its name says; a sheet off the grid maps to the
type whose induced behaviour over the deal space is closest, which is the only thing a posterior over this
grid could ever concentrate on.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `belief` | [BeliefState](../beliefs/BeliefState.md) | *required* |  |
| `deals_arr` | `np.ndarray` | *required* |  |
| `utility` | `np.ndarray` | *required* |  |
| `threshold` | `float` | *required* |  |
