# `RivalPosterior`

What one seat believes about ONE rival's realized valuations, from public information alone.

```python
RivalPosterior(
	*,
	base_values,
	loadings,
	attrs_row,
	beta: float,
	sigma_z: float,
	sigma_eps: float,
	gamma: float = 0.0,
	resale_mean=None,
	n_z: int = 9,
	n_eps: int = 9,
)
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L396-L502)

The rival's value for slot `j` is `round(exp(log B_j + (beta/K) a.w_j + z + eps_j)) + round(gamma R_j)`
with `z` and `eps_j` the only unknowns; both are public-variance Gaussians, so the posterior is the
Gauss-Hermite product grid of :func:`build_type_grid` pushed through the value equation. Because `z` is
shared across the rival's slots, values across slots are CORRELATED within a rival while being independent
across rivals — the affiliation the APV structure is named for [milgrom_weber1982].

The grid is materialized as a flat list of `(z, eps_j)` nodes per slot with a weight vector, which is
what makes conditioning a reweighting: :meth:`condition` multiplies the weights by an indicator on the
node's implied value and renormalizes, so "this rival is still active at price p" and "this rival exited
at p" are the same operation with different bounds.

Parameters
----------
base_values : np.ndarray
    `(n_items,)` public catalogue base values for the stage.
loadings : np.ndarray
    `(n_items, K)` public loadings.
attrs_row : np.ndarray
    `(K,)` the RIVAL's public attribute vector.
beta, sigma_z, sigma_eps : float
    The public structural constants.
gamma : float
    The rival's public resale weight; combined with `resale_mean` when non-zero.
resale_mean : np.ndarray | None
    `(n_items,)` prior mean of the unobserved common resale value, used only when `gamma > 0`. The
    resale component is treated as a known constant at its prior mean rather than a third integrated
    dimension: the design's INTERDEP cells sit in the contingent tail, and the winner's-curse conditioning
    that matters there happens on the SEAT'S OWN signal (see
    :func:`~interlens.arena.auction.bidders.winners_curse_value`), not on the rival grid.
n_z, n_eps : int
    Quadrature node counts.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `base_values` |  | *required* |  |
| `loadings` |  | *required* |  |
| `attrs_row` |  | *required* |  |
| `beta` | `float` | *required* |  |
| `sigma_z` | `float` | *required* |  |
| `sigma_eps` | `float` | *required* |  |
| `gamma` | `float` | `0.0` |  |
| `resale_mean` |  | `None` |  |
| `n_z` | `int` | `9` |  |
| `n_eps` | `int` | `9` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `base_values` |  |  |
| `n_items` |  |  |
| `weights` |  |  |

## Methods {#methods}

## `cdf` {#cdf}

```python
cdf(self, slot: int, x: float) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L469-L471)

`P(v_j <= x)` under the current posterior.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `slot` | `int` | *required* |  |
| `x` | `float` | *required* |  |

## `condition` {#condition}

```python
condition(
	self,
	slot: int,
	*,
	lower: float | None = None,
	upper: float | None = None,
	floor: float = 1e-09,
) -> 'RivalPosterior'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L478-L502)

A COPY of this posterior reweighted by `lower <= v_slot <= upper`.

Every public event a stage reveals is one of these two bounds under a monotone bidding function: a
rival that EXITED an English clock at `p` has `v ~ p` (pass both bounds around `p`); one still
ACTIVE at `p` has `v >= p`; one that LOST a sealed second-price auction at price `p` has
`v <= p`. `floor` is a uniform mass mixed back in after renormalizing — the damping idea from
`negotiation/beliefs.py::BeliefState`, so one surprising observation (a rival bidding above its own
value, which this design MEASURES rather than blocks) cannot collapse the posterior to zero mass.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `slot` | `int` | *required* |  |
| `lower` | `float \| None` | `None` |  |
| `upper` | `float \| None` | `None` |  |
| `floor` | `float` | `1e-09` |  |

## `expected_value` {#expected_value}

```python
expected_value(self, slot: int) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L465-L467)

`E[v_j]` under the current (possibly conditioned) posterior.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `slot` | `int` | *required* |  |

## `node_values` {#node_values}

```python
node_values(self, slot: int) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L452-L454)

The implied whole-number value of `slot` at every grid node (aligned with :attr:`weights`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `slot` | `int` | *required* |  |

## `prob_above` {#prob_above}

```python
prob_above(self, slot: int, x: float) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L473-L475)

`P(v_j > x)` under the current posterior.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `slot` | `int` | *required* |  |
| `x` | `float` | *required* |  |

## `value_pmf` {#value_pmf}

```python
value_pmf(self, slot: int) -> tuple[np.ndarray, np.ndarray]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L456-L463)

The marginal distribution of the rival's value for `slot` as `(values, probs)` with values sorted ascending and duplicate nodes merged.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `slot` | `int` | *required* |  |
