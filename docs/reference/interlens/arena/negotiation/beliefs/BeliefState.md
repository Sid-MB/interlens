# `BeliefState`

A single opponent's belief model: a damped Bayesian posterior over an enumerated `OpponentType` grid, with an optional Hindriks-Tykhonov *separate-learning* factorization for large grids and a frequency-model shadow kept in parallel as the cheap control readout.

```python
BeliefState(
	option_counts,
	types=None,
	*,
	sigma: float = 0.25,
	lam: float = 1.0,
	floor: float = 0.001,
	mode: str = 'auto',
	anchor_first: bool = True,
	joint_cap: int = 20000,
	seed: int = 0,
	tau_levels: tuple = (0.35, 0.55, 0.75),
	max_rankings: int = 24,
)
```

Defined in [`interlens.arena.negotiation.beliefs`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L259-L503)

Parameters
----------
option_counts : sequence[int]
    Per-issue option counts.
types : list[OpponentType] | None
    Explicit grid (else built via `build_type_grid`).
sigma : float
    Concession-likelihood scale `sigma` (Chang-Fujita); larger = softer discrimination.
lam : float
    Damping `lambda in (0, 1]` applied to each observation's log-likelihood (`1` = plain Bayes);
    `< 1` tempers updates so a deceptive trace cannot collapse the posterior.
floor : float
    Uniform mass mixed into the posterior after every update (robustness; keeps every type reachable).
mode : str
    `"joint"` (full product posterior) or `"separate"` (factor into weight / shape / tau marginals,
    each scored against the mean of the others — the AAMAS-2008 scalability trick). `"auto"` picks
    `separate` when the grid exceeds `joint_cap`.
anchor_first : bool
    If True, the first observed offer is scored by how far it sits below each type's *ideal* utility
    (a rational opener bids near its max), which sharpens weight identification early.
joint_cap : int
    Grid-size threshold for `mode="auto"`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `option_counts` |  | *required* |  |
| `types` |  | `None` |  |
| `sigma` | `float` | `0.25` |  |
| `lam` | `float` | `1.0` |  |
| `floor` | `float` | `0.001` |  |
| `mode` | `str` | `'auto'` |  |
| `anchor_first` | `bool` | `True` |  |
| `joint_cap` | `int` | `20000` |  |
| `seed` | `int` | `0` |  |
| `tau_levels` | `tuple` | `(0.35, 0.55, 0.75)` |  |
| `max_rankings` | `int` | `24` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `anchor_first` |  |  |
| `floor` |  |  |
| `lam` |  |  |
| `mode` |  |  |
| `option_counts` |  |  |
| `sigma` |  |  |
| `types` |  |  |

## Methods {#methods}

## `accept_prob` {#accept_prob}

```python
accept_prob(self, deal: Deal) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L418-L420)

Posterior probability the opponent accepts `deal` (mass of types whose utility >= their tau).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## `accept_prob_matrix` {#accept_prob_matrix}

```python
accept_prob_matrix(self, deals_arr: np.ndarray) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L422-L433)

Vectorized `accept_prob` for a whole batch of deals at once: `deals_arr` is the `(D, J)` int option-index array (`GameTables.deals_arr`); returns a `(D,)` acceptance-probability vector.

When the deal batch is the full enumerated space (the common case — the arena passes all deals), this
reuses the precomputed cached `accept_matrix` and collapses to a single `posterior @ accept_matrix`
matmul (the expensive (T x D) utility tensor is built ONCE per game, not per opponent per turn).
Otherwise it builds the tensor on the fly for the given deal subset.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deals_arr` | `np.ndarray` | *required* |  |

## `copy` {#copy}

```python
copy(self) -> 'BeliefState'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L489-L503)

An independent belief with the same posterior, sharing the immutable type grid.

Only the fold state is duplicated (log-posterior, posterior, last observed offer, frequency counts);
the grid arrays and the cached type-by-deal matrices are read-only and shared, so a copy costs two
`|types|` vectors rather than a grid rebuild. This is what :func:`replay_belief` hands callers, so a
cached posterior can never be mutated by whoever received it.

## `expected_normalized_surplus_matrix` {#expected_normalized_surplus_matrix}

```python
expected_normalized_surplus_matrix(self, deals_arr: np.ndarray) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L455-L475)

Posterior-expected **normalized surplus** for a whole batch of deals: `deals_arr` is the `(D, J)` int option-index array (`GameTables.deals_arr`); returns a `(D,)` vector in `[0, 1]`.

Per candidate type, the normalized surplus of a deal is `clip(u_type(d) - tau_type, 0)` divided by
that type's best attainable surplus, so every type contributes on a common `[0, 1]` scale regardless
of the point scale it implies; the readout is then the posterior mixture of those. This is the
opponent-side input the fairness objective needs (`fairness.expected_objective`) and is the exact
analogue of :meth:`accept_prob_matrix`, which mixes the 0/1 *indicator* of the same surplus being
positive — this mixes its magnitude.

Uses the cached type-by-deal matrix when the batch is the full enumerated space (one gemv), and builds
the tensor on the fly otherwise. Both paths normalize by the type's ideal surplus over the WHOLE deal
space (`ideal - tau`, exact for an additive type) rather than over whatever subset was passed, so a
partial batch returns the same numbers as the corresponding slice of a full one.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deals_arr` | `np.ndarray` | *required* |  |

## `expected_utility` {#expected_utility}

```python
expected_utility(self, deal: Deal) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L414-L416)

Posterior-mean opponent utility of `deal`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## `frequency_utility` {#frequency_utility}

```python
frequency_utility(self, deal: Deal) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L485-L487)

The cheap frequency-model readout of the opponent's utility of `deal` (control comparison).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## `induced_distribution` {#induced_distribution}

```python
induced_distribution(self)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L410-L412)

The induced distribution over `(utility_fn, threshold)`: a list of `(OpponentType, prob)`.

## `map_type` {#map_type}

```python
map_type(self) -> OpponentType
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L406-L408)

Maximum-a-posteriori opponent type.

## `observe` {#observe}

```python
observe(self, offer: Deal) -> 'BeliefState'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L328-L347)

Update the posterior from one observed opponent offer (a proposed `Deal`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offer` | `Deal` | *required* |  |

## `observe_response` {#observe_response}

```python
observe_response(
	self,
	deal: Deal,
	accepted: bool,
	*,
	reliability: float = 0.75,
	strength: float = 0.35,
) -> 'BeliefState'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L349-L371)

Soft-update from an opponent's public accept/reject response to `deal`.

A type predicts acceptance iff the deal clears its reservation threshold.  `reliability` is the
probability that the observed response follows that myopic prediction; values below 1 explicitly
allow strategic rejection, mistakes, and cheap-talk inconsistency.  `strength` tempers this evidence
relative to a self-authored proposal, because a vote is informative about the threshold but much less
diagnostic of the opponent's complete preference ordering.

The update is deliberately soft and implementable: it consumes only a public formal response and the
referenced public deal, never the opponent's hidden score sheet.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |
| `accepted` | `bool` | *required* |  |
| `reliability` | `float` | `0.75` |  |
| `strength` | `float` | `0.35` |  |

## `posterior` {#posterior}

```python
posterior(self) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L381-L386)

Posterior probability vector aligned with `self.types`.

Under `mode="separate"` this is the
product-of-marginals reconstruction (weights, shapes, tau treated independent).

## `threshold_distribution` {#threshold_distribution}

```python
threshold_distribution(self)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L477-L483)

Posterior distribution over the opponent's reservation `tau`: `{tau: prob}`.

## `type_thresholds` {#type_thresholds}

```python
type_thresholds(self) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L435-L440)

The `(|types|,)` reservation `tau` of every grid type, aligned with `self.types` (read-only on the shared default grid).

The vector form of the per-type `threshold` attribute, exposed so a
diagnostic can compare a whole grid against a known reservation without rebuilding it from the
dataclasses.

## `type_utility_matrix` {#type_utility_matrix}

```python
type_utility_matrix(self, deals_arr: np.ndarray) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L442-L453)

The `(|types|, D)` per-type utility tensor for a batch of deals: entry `[t, d]` is type `t`'s `[0, 1]`-scale utility of deal `d`.

The raw quantity :meth:`accept_prob_matrix` thresholds and :meth:`expected_normalized_surplus_matrix`
rescales, exposed because a *diagnostic* needs the utilities themselves — posterior-expected opponent
utility is `posterior() @ type_utility_matrix(...)`, one gemv. Returns the cached read-only tensor
when the batch is the full enumerated space (the common case) and builds it on the fly otherwise, so
the two paths agree numerically.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deals_arr` | `np.ndarray` | *required* |  |
