# `solve_equilibrium`

Damped fixed-point solve for the Banks-Duggan stationary continuation values.

```python
solve_equilibrium(
	tables: GameTables,
	*,
	discount: float = 0.95,
	thresholds=None,
	proposer_probs=None,
	damping: float = 0.5,
	max_iter: int = 1000,
	tol: float = 1e-09,
	tie_temperature: float = 0.0,
	v_init=None,
) -> EquilibriumSolution
```

Defined in [`interlens.arena.negotiation.equilibrium`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/equilibrium.py#L80-L147)

Parameters
----------
tables : GameTables
    Utility tables for the game.
discount : float
    Common discount `delta` in `(0, 1]`.
thresholds : sequence[float] | None
    Disagreement flows `tau_i` (default: `tables.thresholds`).
proposer_probs : sequence[float] | None
    Recognition probabilities `p_j` (default uniform `1/n`).
damping : float
    Relaxation `lambda` in `(0, 1]` for `v <- (1-lambda) v + lambda T(v)`.
max_iter, tol : int, float
    Iteration budget and convergence tolerance on the residual.
tie_temperature : float
    If `> 0`, the proposer's outcome is a softmax-over-`A(v)` average of utilities (smooths cycles)
    rather than a hard best-in-set.
v_init : sequence[float] | None
    Optional initial `v` (default column means of utility).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
| `discount` | `float` | `0.95` |  |
| `thresholds` |  | `None` |  |
| `proposer_probs` |  | `None` |  |
| `damping` | `float` | `0.5` |  |
| `max_iter` | `int` | `1000` |  |
| `tol` | `float` | `1e-09` |  |
| `tie_temperature` | `float` | `0.0` |  |
| `v_init` |  | `None` |  |
