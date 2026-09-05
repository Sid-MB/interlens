# `ValueModel`

One stage's allocation problem: the realized value table plus every structural parameter the bundle value depends on.

```python
ValueModel(
	values: np.ndarray,
	capacities: tuple[int, ...],
	decays: tuple[float, ...],
	synergy_rates: tuple[float, ...],
	synergy_targets: tuple[tuple[int, ...] | None, ...],
	budgets: tuple[int, ...] | None = None,
)
```

Defined in [`interlens.arena.auction.allocation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L158-L313)

Parameters
----------
values : np.ndarray
    `(n_bidders, n_items)` realized whole-number valuations `v_ij`.
capacities : tuple[int, ...]
    Per-seat maximum number of lots `k_i`.
decays : tuple[float, ...]
    Per-seat diminishing-returns factor `d_i` in `(0, 1]`.
synergy_rates : tuple[float, ...]
    Per-seat complementarity rate `c_i` (public).
synergy_targets : tuple[tuple[int, ...] | None, ...]
    Per-seat private target SET (`None` when the seat has no synergy).
budgets : tuple[int, ...] | None
    Per-seat whole-number stage budget, used by :meth:`budget_feasible` and the payment collectability
    checks. It does NOT enter :meth:`efficient_allocation`: a budget binds on PAYMENTS, which depend on
    the mechanism, while the efficient allocation is a property of values alone. Design.md §5.1's
    "allocations respecting every capacity and budget" is therefore implemented as a capacity-exact
    optimum plus an explicit budget-feasibility report, rather than by folding a price-dependent
    constraint into a value-only optimization (a resolved design ambiguity).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `values` | `np.ndarray` | *required* |  |
| `capacities` | `tuple[int, ...]` | *required* |  |
| `decays` | `tuple[float, ...]` | *required* |  |
| `synergy_rates` | `tuple[float, ...]` | *required* |  |
| `synergy_targets` | `tuple[tuple[int, ...] \| None, ...]` | *required* |  |
| `budgets` | `tuple[int, ...] \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `budgets` | `tuple[int, ...] \| None` |  |
| `capacities` | `tuple[int, ...]` |  |
| `decays` | `tuple[float, ...]` |  |
| `n_bidders` | `int` | Number of seats. |
| `n_items` | `int` | Number of lots. |
| `synergy_rates` | `tuple[float, ...]` |  |
| `synergy_targets` | `tuple[tuple[int, ...] \| None, ...]` |  |
| `values` | `np.ndarray` |  |

## Methods {#methods}

## `budget_feasible` {#budget_feasible}

```python
budget_feasible(self, alloc: Allocation, payments) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L230-L235)

Whether every winner can pay its assigned payment out of its stage budget.

`True` when the model
carries no budgets.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `alloc` | [Allocation](Allocation.md) | *required* |  |
| `payments` |  | *required* |  |

## `bundle_value` {#bundle_value}

```python
bundle_value(self, seat: int, bundle) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L210-L224)

`V_i(S)` per design.md §2.2: decayed sum over the bundle sorted descending, plus the synergy bonus when the bundle CONTAINS the private target set, and `-inf` when capacity is exceeded.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |
| `bundle` |  | *required* |  |

## `efficient_allocation` {#efficient_allocation}

```python
efficient_allocation(self) -> tuple[Allocation, float]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L265-L298)

The welfare-maximizing allocation and its welfare, solved EXACTLY.

Enumerates the subsets of synergy-capable seats whose target set is fully awarded (skipping patterns
whose targets overlap or exceed a capacity), solves each as a maximum-weight assignment over ranked
capacity slots plus unsold slots, adds the activation bonuses, and takes the best. Ties are broken by
the enumeration order (empty activation first, then ascending seat subsets), so the result is
deterministic — which the S1 uniqueness screen depends on.

## `from_spec` {#from_spec}

```python
from_spec(spec, t: int) -> 'ValueModel'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L191-L197)

Build the value model for stage `t` (1-indexed) of an :class:`~.spec.AuctionSpec`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `spec` |  | *required* |  |
| `t` | `int` | *required* |  |

## `max_welfare` {#max_welfare}

```python
max_welfare(self) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L300-L302)

Welfare of the efficient allocation — the denominator of `efficiency_t` (design.md §5.1).

## `welfare` {#welfare}

```python
welfare(self, alloc: Allocation) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L226-L228)

Realized welfare of an allocation: the sum of every winner's bundle value.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `alloc` | [Allocation](Allocation.md) | *required* |  |

## `welfare_without` {#welfare_without}

```python
welfare_without(self, seat: int) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L304-L313)

Maximum welfare of the OTHER seats when `seat` is absent — the counterfactual the VCG pivot payment charges.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |
