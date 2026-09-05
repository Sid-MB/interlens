# `condition_on_commit`

Fold a declared normalized walk-away floor into the posterior over the grid's reservation levels: a Gaussian log-likelihood `-(tau - floor)^2 / (2 scale^2)` per type, tempered by `strength` and `lam`.

```python
condition_on_commit(
	bst: BeliefState,
	floor_norm: float,
	*,
	scale: float = 0.12,
	strength: float = 0.6,
) -> None
```

Defined in [`interlens.arena.negotiation.talking`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L240-L248)

The declarer's floor is on its own min-max scale and a grid type's `tau` on the type's additive [0, 1]
scale — close but not identical coordinates, which is one reason this update is soft.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bst` | [BeliefState](../beliefs/BeliefState.md) | *required* |  |
| `floor_norm` | `float` | *required* |  |
| `scale` | `float` | `0.12` |  |
| `strength` | `float` | `0.6` |  |
