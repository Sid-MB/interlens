# `Mechanism`

The auction format as a CONFIG, never a separate runner (design.md §3).

```python
Mechanism(
	family: str,
	pricing: str,
	n_items: int = 1,
	n_units: int = 1,
	increment: int = DEFAULT_INCREMENT,
	start_price: int = DEFAULT_RESERVE,
	reserve: int = DEFAULT_RESERVE,
	round_cap: int = 1,
	activity_rule: str = 'none',
	bid_granularity: int = DEFAULT_BID_GRANULARITY,
)
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L141-L260)

Parameters
----------
family : str
    One of :data:`FAMILIES`; fixes the round structure and the action grammar.
pricing : str
    What the winner pays; must be legal for `family` per :data:`PRICING_BY_FAMILY`.
n_items : int
    Number of distinct lots auctioned per stage (1 for the single-item families).
n_units : int
    Number of identical units for the multi-unit families (`uniform_price` / `clinching`); 1 elsewhere.
increment : int
    Minimum whole-number bid increment, and the clock step for the ascending/descending families.
start_price : int
    Clock start. Ascending clocks start at `reserve`; a descending (Dutch) clock starts above the
    maximum realized valuation, which the generator sets per stage.
reserve : int
    Reserve price; a lot below reserve goes unsold.
round_cap : int
    Hard cap on bidding rounds within one stage. For clock families it is set so the clock can exceed the
    maximum realized valuation; hitting it stamps the stage `clock_ceiling` (G1 fails a cell above 5%).
activity_rule : str
    `"none"` or `"eligibility_ratchet"` — under the ratchet a bidder that passes on lot j in round r
    may not bid on j later in that stage (design.md §3.3, SAA).
bid_granularity : int
    Bids must be multiples of this. `1` is the open channel; setting it to `increment` is the
    bid-rounding sub-arm that CLOSES the trailing-digit channel (design.md §8).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `family` | `str` | *required* |  |
| `pricing` | `str` | *required* |  |
| `n_items` | `int` | `1` |  |
| `n_units` | `int` | `1` |  |
| `increment` | `int` | `DEFAULT_INCREMENT` |  |
| `start_price` | `int` | `DEFAULT_RESERVE` |  |
| `reserve` | `int` | `DEFAULT_RESERVE` |  |
| `round_cap` | `int` | `1` |  |
| `activity_rule` | `str` | `'none'` |  |
| `bid_granularity` | `int` | `DEFAULT_BID_GRANULARITY` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `activity_rule` | `str` |  |
| `bid_granularity` | `int` |  |
| `family` | `str` |  |
| `increment` | `int` |  |
| `is_clock` | `bool` | Whether the format runs a price clock across rounds rather than one sealed round. |
| `is_multi_item` | `bool` | Whether a stage allocates more than one distinct lot (the combinatorial/exposure regime). |
| `n_items` | `int` |  |
| `n_units` | `int` |  |
| `pricing` | `str` |  |
| `reserve` | `int` |  |
| `round_cap` | `int` |  |
| `start_price` | `int` |  |

## Methods {#methods}

## `clinching` {#clinching}

```python
clinching(n_units: int = 3, **kw={}) -> 'Mechanism'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L234-L238)

Ausubel ascending clock on `n_units` identical units [ausubel2004, pp. 1454-1460].

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_units` | `int` | `3` |  |
| `kw` |  | `{}` |  |

## `dutch` {#dutch}

```python
dutch(**kw={}) -> 'Mechanism'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L213-L218)

Descending clock, nothing revealed between rounds — strategically equivalent to first-price [vickrey1961, pp. 20-23], which is why no separate sealed first-price cell exists.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `kw` |  | `{}` |  |

## `english` {#english}

```python
english(**kw={}) -> 'Mechanism'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L207-L211)

Ascending clock with public irrevocable exits; the winner pays the second-to-last exit price.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `kw` |  | `{}` |  |

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'Mechanism'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L257-L260)

Rebuild a :class:`Mechanism` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `saa` {#saa}

```python
saa(n_items: int, **kw={}) -> 'Mechanism'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L220-L227)

Simultaneous ascending auction on `n_items` lots with the eligibility ratchet.

The round cap
follows the lot count (3 at the small pilot rung, 5 at 20 lots) unless overridden.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_items` | `int` | *required* |  |
| `kw` |  | `{}` |  |

## `sealed` {#sealed}

```python
sealed(pricing: str = 'second_price', **kw={}) -> 'Mechanism'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L202-L205)

One simultaneous sealed bidding round (design.md §3.3 row 1).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `pricing` | `str` | `'second_price'` |  |
| `kw` |  | `{}` |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L250-L255)

JSON-ready dict of every mechanism field.

## `uniform_price` {#uniform_price}

```python
uniform_price(n_units: int = 3, **kw={}) -> 'Mechanism'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L229-L232)

Sealed uniform-price sale of `n_units` identical units; winners pay the highest rejected bid.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_units` | `int` | `3` |  |
| `kw` |  | `{}` |  |
