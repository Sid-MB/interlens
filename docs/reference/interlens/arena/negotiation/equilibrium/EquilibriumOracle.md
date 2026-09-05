# `EquilibriumOracle`

Mounts the stationary equilibrium as a per-turn reference: what the standing offer *should* look like for whichever seat currently proposes, plus the proposer-power decomposition `v*`.

```python
EquilibriumOracle(
	agent: int | None = None,
	*,
	discount: float | None = None,
	damping: float = 0.5,
	max_iter: int = 1000,
	tol: float = 1e-09,
	tie_temperature: float = 0.0,
	proposer_probs=None,
)
```

Defined in [`interlens.arena.negotiation.equilibrium`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/equilibrium.py#L175-L256)

**Inherits from:** [Oracle](../../oracles/Oracle.md)

Parameters mirror `solve_equilibrium` (`discount`/`damping`/`max_iter`/`tol`/
`tie_temperature`/`proposer_probs`). `discount` defaults to `None` = read the game's own
`discount` / `breakdown_risk` (single source of truth). `agent` (optional) is the seat whose actions
are valued.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agent` | `int \| None` | `None` |  |
| `discount` | `float \| None` | `None` |  |
| `damping` | `float` | `0.5` |  |
| `max_iter` | `int` | `1000` |  |
| `tol` | `float` | `1e-09` |  |
| `tie_temperature` | `float` | `0.0` |  |
| `proposer_probs` |  | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `agent` |  |  |
| `damping` |  |  |
| `discount` |  |  |
| `max_iter` |  |  |
| `name` |  |  |
| `proposer_probs` |  |  |
| `tie_temperature` |  |  |
| `tol` |  |  |

## Methods {#methods}

## `evaluate` {#evaluate}

```python
evaluate(self, game, history, agent, legal)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/equilibrium.py#L214-L256)

Value the current proposer's legal `Propose` actions against the equilibrium best-in-set: the equilibrium proposal is `best`; each `Propose(deal)` is valued by the proposer's utility of that deal (0 outside the social acceptance set is not imposed — the value is the raw utility, and the flag `outside_social_set` marks proposals `A(v*)` would not sustain).

`extra` carries `v*` and the
per-proposer equilibrium deals.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `history` |  | *required* |  |
| `agent` |  | *required* |  |
| `legal` |  | *required* |  |

## `solve` {#solve}

```python
solve(self, game) -> EquilibriumSolution
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/equilibrium.py#L198-L212)

Solve the stationary equilibrium for `game` (cached on the game object).

The discount is read
from the game (`effective_discount`) unless an explicit override was passed to the constructor.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
