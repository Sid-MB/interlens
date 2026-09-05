# `EquilibriumSolution`

Result of the fixed-point solve.

```python
EquilibriumSolution(
	values: np.ndarray,
	proposals: dict,
	residual: float,
	converged: bool,
	social_set_size: int,
)
```

Defined in [`interlens.arena.negotiation.equilibrium`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/equilibrium.py#L55-L77)

Attributes
----------
values : np.ndarray
    Stationary continuation values `v*` (shape `(n,)`).
proposals : dict[int, int]
    Per-proposer equilibrium deal index `x_j*` (`-1` if the proposer delays / no social set).
residual : float
    Final fixed-point residual `max|T(v) - v|`.
converged : bool
    Whether `residual < tol` within `max_iter`.
social_set_size : int
    `|A(v*)|` at the solution.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `values` | `np.ndarray` | *required* |  |
| `proposals` | `dict` | *required* |  |
| `residual` | `float` | *required* |  |
| `converged` | `bool` | *required* |  |
| `social_set_size` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `converged` | `bool` |  |
| `proposals` | `dict` |  |
| `residual` | `float` |  |
| `social_set_size` | `int` |  |
| `values` | `np.ndarray` |  |
