# `StageOutcome`

One stage's realized numbers and its benchmark, in the shape every stage metric consumes.

```python
StageOutcome(
	stage: int,
	values: np.ndarray,
	bids: np.ndarray,
	benchmark_bids: np.ndarray,
	winner_of: tuple,
	payments: np.ndarray,
	bundle_values: np.ndarray,
	max_welfare: float,
	budgets: np.ndarray,
	exposure_seats: tuple = (),
	truthful_bids: np.ndarray | None = None,
	censored_bids: np.ndarray | None = None,
	suppression_scope: str = 'losers',
)
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L60-L135)

Attributes
----------
stage : int
    1-indexed stage.
values : np.ndarray
    `(n_bidders, n_items)` realized valuations.
bids : np.ndarray
    `(n_bidders, n_items)` the priced action each seat took, `nan` where it took none. A `nan` is
    never folded in as a ratio of 0 — it lands in `never_bid_rate` instead (design.md §5.1).
benchmark_bids : np.ndarray
    `(n_bidders, n_items)` the PRIMARY equilibrium benchmark from :mod:`.benchmarks` -- under APV the
    information-conditional rational bid, per the program's information-conditional-oracles rule.
truthful_bids : np.ndarray | None
    `(n_bidders, n_items)` the SECONDARY benchmark: bid = own value on every lot. Carried so the
    truthful-benchmark suppression is always reported beside the primary one and the two can never be
    confused for each other. `None` where the two coincide (every single-lot private-values family).
winner_of : tuple[int | None, ...]
    Realized allocation, per lot.
payments : np.ndarray
    `(n_bidders,)` realized payment per seat.
bundle_values : np.ndarray
    `(n_bidders,)` realized bundle value per seat (capacity, decay and synergy applied).
max_welfare : float
    Welfare of the efficient allocation — the efficiency denominator.
budgets : np.ndarray
    `(n_bidders,)` stage budgets, for the violation and collectability checks.
exposure_seats : tuple[int, ...]
    Seats that won part but not all of their private synergy target set — the exposure problem realized.
censored_bids : np.ndarray | None
    `(n_bidders, n_items)` an UPPER BOUND on the bid of each seat that took no priced action, `nan`
    where no bound exists. Only a descending clock produces one: a seat that never claimed revealed that
    it would not take the lot at any price at or above the price the clock stopped at, so that price
    bounds its bid from above. Suppression computed from an upper bound on the bid is a conservative
    LOWER bound on suppression, which is why the bound is worth recording rather than discarding.
suppression_scope : str
    Which `(seat, lot)` cells the stage's PRIMARY suppression averages over — fixed by the mechanism,
    carried on the outcome so every stored stage row says which definition produced its number. See
    :func:`suppression`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int` | *required* |  |
| `values` | `np.ndarray` | *required* |  |
| `bids` | `np.ndarray` | *required* |  |
| `benchmark_bids` | `np.ndarray` | *required* |  |
| `winner_of` | `tuple` | *required* |  |
| `payments` | `np.ndarray` | *required* |  |
| `bundle_values` | `np.ndarray` | *required* |  |
| `max_welfare` | `float` | *required* |  |
| `budgets` | `np.ndarray` | *required* |  |
| `exposure_seats` | `tuple` | `()` |  |
| `truthful_bids` | `np.ndarray \| None` | `None` |  |
| `censored_bids` | `np.ndarray \| None` | `None` |  |
| `suppression_scope` | `str` | `'losers'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `benchmark_bids` | `np.ndarray` |  |
| `bids` | `np.ndarray` |  |
| `budgets` | `np.ndarray` |  |
| `bundle_values` | `np.ndarray` |  |
| `censored_bids` | `np.ndarray \| None` |  |
| `exposure_seats` | `tuple` |  |
| `max_welfare` | `float` |  |
| `n_bidders` | `int` | Number of seats. |
| `n_items` | `int` | Number of lots. |
| `payments` | `np.ndarray` |  |
| `realized_welfare` | `float` | Sum of the winners' bundle values. |
| `stage` | `int` |  |
| `suppression_scope` | `str` |  |
| `truthful_bids` | `np.ndarray \| None` |  |
| `values` | `np.ndarray` |  |
| `winner_of` | `tuple` |  |

## Methods {#methods}

## `won` {#won}

```python
won(self, seat: int) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L133-L135)

Whether `seat` won at least one lot.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |
