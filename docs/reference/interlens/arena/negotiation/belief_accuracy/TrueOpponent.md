# `TrueOpponent`

One opponent's ground truth, precomputed once per episode against a fixed deal ordering.

```python
TrueOpponent(
	utility: np.ndarray,
	threshold: float,
	accepts: np.ndarray,
	type_index: int,
	type_distance: float,
)
```

Defined in [`interlens.arena.negotiation.belief_accuracy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/belief_accuracy.py#L61-L85)

Attributes
----------
utility : np.ndarray
    `(D,)` true utility on the type grid's `[0, 1]` scale (min-max over the deal space).
threshold : float
    The true reservation on that same scale.
accepts : np.ndarray
    `(D,)` bool — the true accept set, read off RAW points (`utility >= threshold`) so no normalization
    can move its boundary.
type_index : int
    Index into the belief grid of the type nearest this sheet (:func:`nearest_type_index`).
type_distance : float
    That type's distance (0.0 when the sheet lies exactly on the grid), kept so a caller can report how
    well the grid could POSSIBLY have done before reading how well it did.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `utility` | `np.ndarray` | *required* |  |
| `threshold` | `float` | *required* |  |
| `accepts` | `np.ndarray` | *required* |  |
| `type_index` | `int` | *required* |  |
| `type_distance` | `float` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `accepts` | `np.ndarray` |  |
| `threshold` | `float` |  |
| `type_distance` | `float` |  |
| `type_index` | `int` |  |
| `utility` | `np.ndarray` |  |
