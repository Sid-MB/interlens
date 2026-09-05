# `AcceptanceOracle`

Values accept / reject / propose / walk at one turn via optimal stopping.

```python
AcceptanceOracle(
	agent: int,
	*,
	discount: float | None = None,
	cost: float = 0.0,
	flow: float = 0.0,
	accept_prob_fn=None,
	outside_value: float | None = None,
	accept_prob_vec=None,
)
```

Defined in [`interlens.arena.negotiation.acceptance`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/acceptance.py#L164-L279)

**Inherits from:** [Oracle](../../oracles/Oracle.md)

Parameters
----------
agent : int
    The deciding seat.
discount : float
    Per-round discount `delta` OVERRIDE. Default `None` = read the game's own `discount` /
    `breakdown_risk` via `effective_discount` (single source of truth); pass a float only to force a
    value. A nonzero discount is what makes interior concession rational (Sandholm-Vulkan, module
    docstring).
cost : float
    Additive per-round search cost `C`.
flow : float
    Disagreement flow while unagreed.
accept_prob_fn : callable | None
    `deal -> P(all opponents accept)` from the belief oracle; None = full-info uniform-offer proxy.
accept_prob_vec : np.ndarray | None
    The vectorized form of `accept_prob_fn`: a `(|D|,)` array of the same probabilities in
    `tables.deals` order (see :func:`offer_surplus_pmf`). Prefer it — a caller that already holds the
    posterior acceptance table can produce it with ONE `passage_probability` call, where the callable
    form re-solves the same Poisson-binomial once per deal. Takes precedence over `accept_prob_fn`.
outside_value : float | None
    Optional reservation floor (outside option).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agent` | `int` | *required* |  |
| `discount` | `float \| None` | `None` |  |
| `cost` | `float` | `0.0` |  |
| `flow` | `float` | `0.0` |  |
| `accept_prob_fn` |  | `None` |  |
| `outside_value` | `float \| None` | `None` |  |
| `accept_prob_vec` |  | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `accept_prob_fn` |  |  |
| `accept_prob_vec` |  |  |
| `agent` |  |  |
| `cost` |  |  |
| `discount` |  |  |
| `flow` |  |  |
| `name` |  |  |
| `outside_value` |  |  |

## Methods {#methods}

## `evaluate` {#evaluate}

```python
evaluate(self, game, history, agent, legal)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/acceptance.py#L238-L279)

Value each legal action in surplus units and flag stopping errors.

`Accept(offer_id)` is valued at its realized surplus for `agent`; `Reject`/`Propose`/`Walk`
are valued at the continuation reservation `v` (Walk clamped at >= 0). The discount is read from the
game (`effective_discount`) unless the oracle was constructed with an explicit override. Flags:
`premature_accept` (an available Accept is below reservation), `should_accept` (the best live offer
clears reservation), `deadline_brinkmanship` (delta ~ 1 with a hard deadline).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `history` |  | *required* |  |
| `agent` |  | *required* |  |
| `legal` |  | *required* |  |

## `reservation` {#reservation}

```python
reservation(
	self,
	tables: GameTables,
	rounds_left: int,
	discount: float | None = None,
	agent: int | None = None,
	*,
	objective=None,
) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/acceptance.py#L208-L227)

The reservation surplus `v_{rounds_left}` given the belief-induced offer distribution.

`agent` is the seat whose offer-surplus distribution sets the reservation; `None` falls back to the
constructor's `self.agent`. Pass it whenever one instance serves several seats (a scenario's shared
oracle stack) — :meth:`evaluate` passes the seat it resolved, since a stale seat here would silently set
every party's stopping threshold from seat 0's sheet and so mis-flag `premature_accept` /
`should_accept`.

`objective` substitutes a table-level payoff column for own surplus (see :func:`offer_surplus_pmf`),
which is what turns this into a fairness-seeking agent's stopping rule: the returned number is then the
table welfare it expects to reach by continuing, and it should accept iff the standing offer's welfare
clears it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
| `rounds_left` | `int` | *required* |  |
| `discount` | `float \| None` | `None` |  |
| `agent` | `int \| None` | `None` |  |
| `objective` |  | `None` |  |

## `reservation_curve` {#reservation_curve}

```python
reservation_curve(
	self,
	tables: GameTables,
	T: int,
	discount: float | None = None,
	agent: int | None = None,
) -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/acceptance.py#L229-L236)

The full endogenous reservation curve `tau_i(rounds_left)` for `rounds_left = 0..T`.

`agent` as
in :meth:`reservation`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
| `T` | `int` | *required* |  |
| `discount` | `float \| None` | `None` |  |
| `agent` | `int \| None` | `None` |  |
