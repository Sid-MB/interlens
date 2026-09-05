# `Benchmark`

One stage's equilibrium reference outcome.

```python
Benchmark(
	label: str,
	citation_key: str,
	bids: np.ndarray,
	alloc: Allocation,
	prices: np.ndarray,
	payments: np.ndarray,
	welfare: float,
	revenue: float,
	note: str = '',
	detail: dict = dict(),
)
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L56-L95)

Attributes
----------
label : str
    Short name of the benchmark (`"truthful"`, `"rnne"`, `"straightforward"`, ...).
citation_key : str
    Key into :data:`~interlens.arena.auction.references.REFERENCES` for the result this implements.
bids : np.ndarray
    `(n_bidders, n_items)` equilibrium bid per seat and lot; `nan` where the benchmark prescribes no
    priced action. This is the numerator side of every suppression measurement.
alloc : Allocation
    Who wins under the benchmark bids.
prices : np.ndarray
    `(n_items,)` price paid per lot (0 where unsold).
payments : np.ndarray
    `(n_bidders,)` total payment per seat.
welfare : float
    Realized welfare of `alloc` under the true values.
revenue : float
    Total payments.
note : str
    What the benchmark assumes, in one line — carried on the object so an analysis table can print the
    assumption beside the number instead of relying on the reader knowing it.
detail : dict
    Anything format-specific (e.g. per-lot standing-price paths for SAA).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `label` | `str` | *required* |  |
| `citation_key` | `str` | *required* |  |
| `bids` | `np.ndarray` | *required* |  |
| `alloc` | [Allocation](../allocation/Allocation.md) | *required* |  |
| `prices` | `np.ndarray` | *required* |  |
| `payments` | `np.ndarray` | *required* |  |
| `welfare` | `float` | *required* |  |
| `revenue` | `float` | *required* |  |
| `note` | `str` | `''` |  |
| `detail` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `alloc` | [Allocation](../allocation/Allocation.md) |  |
| `bids` | `np.ndarray` |  |
| `citation_key` | `str` |  |
| `detail` | `dict` |  |
| `label` | `str` |  |
| `note` | `str` |  |
| `payments` | `np.ndarray` |  |
| `prices` | `np.ndarray` |  |
| `revenue` | `float` |  |
| `welfare` | `float` |  |
