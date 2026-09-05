# `AuctionState`

Everything a :class:`AuctionPolicy` needs to compute its next move — the machine-readable counterpart of the text view an LLM seat reads, so the two kinds of seat are interchangeable.

```python
AuctionState(
	seat: int,
	spec: object,
	stage: int,
	values: np.ndarray,
	budget: int,
	posteriors: list = list(),
	round: int = 1,
	synergy_target: tuple[int, ...] | None = None,
	signals: np.ndarray | None = None,
	standing: list | None = None,
	standing_winner: list | None = None,
	clock_price: int | None = None,
	active: tuple[int, ...] = (),
	exits: dict = dict(),
	oracle_values: np.ndarray | None = None,
	reserve: int = 0,
	increment: int = 1,
)
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L83-L184)

Attributes
----------
seat : int
    This policy's seat index.
spec : AuctionSpec
    The episode spec (public structure; the private stage draws are surfaced through the fields below,
    never read off the spec by a private-information policy).
stage, round : int
    1-indexed stage within the episode and round within the stage.
values : np.ndarray
    `(n_items,)` this seat's OWN known valuation component. Under IPV/APV that is the realized value;
    under INTERDEP it is the private part only, with the common component reachable solely through
    `signals` — which is exactly the information split that makes a winner's curse possible.
budget : int
    This seat's remaining whole-number budget for the stage.
synergy_target : tuple[int, ...] | None
    This seat's private target set, or `None`.
signals : np.ndarray | None
    `(n_items,)` private noisy resale signals (INTERDEP only).
posteriors : list[RivalPosterior]
    Public-information posteriors over every seat, index-aligned with seats (this seat's own entry is
    present but unused). Built by :func:`public_posteriors`.
standing : list[int] | None
    Per-lot standing high price, or `None` where no bid stands.
standing_winner : list[int | None] | None
    Per-lot standing high bidder.
clock_price : int | None
    Current clock price for the clock families.
active : tuple[int, ...]
    Seats still active on the clock.
exits : dict[int, int]
    Observed public exits this stage: seat -> the clock price it exited at. A conditional-Bayes seat
    folds these into its posteriors, which is the whole content of "updates on observed public events
    within a stage".
oracle_values : np.ndarray | None
    `(n_bidders, n_items)` everyone's realized valuations. Present only for an `information="oracle"`
    seat; a private-information policy must never read it, which the policies below enforce by taking it
    only through :meth:`AuctionPolicy._rival_values`.
reserve, increment : int
    Mechanism parameters, carried so a policy never re-defaults them.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |
| `spec` | `object` | *required* |  |
| `stage` | `int` | *required* |  |
| `values` | `np.ndarray` | *required* |  |
| `budget` | `int` | *required* |  |
| `posteriors` | `list` | `list()` |  |
| `round` | `int` | `1` |  |
| `synergy_target` | `tuple[int, ...] \| None` | `None` |  |
| `signals` | `np.ndarray \| None` | `None` |  |
| `standing` | `list \| None` | `None` |  |
| `standing_winner` | `list \| None` | `None` |  |
| `clock_price` | `int \| None` | `None` |  |
| `active` | `tuple[int, ...]` | `()` |  |
| `exits` | `dict` | `dict()` |  |
| `oracle_values` | `np.ndarray \| None` | `None` |  |
| `reserve` | `int` | `0` |  |
| `increment` | `int` | `1` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `active` | `tuple[int, ...]` |  |
| `budget` | `int` |  |
| `clock_price` | `int \| None` |  |
| `exits` | `dict` |  |
| `increment` | `int` |  |
| `n_items` | `int` | Number of lots this stage. |
| `oracle_values` | `np.ndarray \| None` |  |
| `posteriors` | `list` |  |
| `reserve` | `int` |  |
| `rivals` | `tuple[int, ...]` | Seat indices of the other bidders. |
| `round` | `int` |  |
| `seat` | `int` |  |
| `signals` | `np.ndarray \| None` |  |
| `spec` | `object` |  |
| `stage` | `int` |  |
| `standing` | `list \| None` |  |
| `standing_winner` | `list \| None` |  |
| `synergy_target` | `tuple[int, ...] \| None` |  |
| `values` | `np.ndarray` |  |

## Methods {#methods}

## `from_spec` {#from_spec}

```python
from_spec(
	spec,
	t: int,
	seat: int,
	*,
	information: str = 'private',
	round: int = 1,
	**kw={},
) -> 'AuctionState'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L148-L165)

Build the stage-`t` state for `seat` straight from a spec — the constructor the tests, the per-turn counterfactual annotator, and a solo harness all use.

`information="oracle"` additionally
attaches every seat's realized values.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `spec` |  | *required* |  |
| `t` | `int` | *required* |  |
| `seat` | `int` | *required* |  |
| `information` | `str` | `'private'` |  |
| `round` | `int` | `1` |  |
| `kw` |  | `{}` |  |

## `value_model` {#value_model}

```python
value_model(self) -> ValueModel
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L177-L184)

A one-seat :class:`~.allocation.ValueModel` over this seat's own values — what the bundle and capacity arithmetic in the multi-item formats runs against.
