# `AuctionSpec`

A complete repeated-auction episode specification (design.md §2.1).

```python
AuctionSpec(
	item_slots: tuple[ItemSlot, ...],
	attr_names: tuple[str, ...],
	bidders: tuple[BidderSpec, ...],
	horizon: int,
	stages: tuple[StageDraw, ...],
	mechanism: Mechanism,
	beta: float = DEFAULT_BETA,
	sigma_z: float = DEFAULT_SIGMA_Z,
	sigma_eps: float = DEFAULT_SIGMA_EPS,
	sigma_nu: float = DEFAULT_SIGMA_NU,
	value_structure: str = 'apv',
	channel: str = 'silent',
	dm_cap: int = DEFAULT_DM_CAP,
	talk_rounds: int = DEFAULT_TALK_ROUNDS,
	disclose_public_facts: bool = False,
	ring: RingSpec | None = None,
	framing: str = 'datacenter',
	meta: dict = dict(),
)
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L444-L652)

Parameters
----------
item_slots : tuple[ItemSlot, ...]
    The persistent catalogue; `len` must equal `mechanism.n_items`.
attr_names : tuple[str, ...]
    Names of the `K` public attribute dimensions, aligned with every `a_i` and `w_j`.
beta, sigma_z, sigma_eps, sigma_nu : float
    The PUBLIC structural constants of the generative model, announced in the rules so a rival can
    compute a genuinely informative posterior (design.md §2.2).
bidders : tuple[BidderSpec, ...]
    Exactly :data:`N_BIDDERS` seats; personas persist across stages.
horizon : int
    `T`, the number of auction stages in the episode. `len(stages)` must equal it.
stages : tuple[StageDraw, ...]
    The frozen per-stage realizations, in stage order.
mechanism : Mechanism
    The format config. Formats never fork a runner.
value_structure : str
    One of :data:`VALUE_STRUCTURES`; consistency with `beta`/`sigma_z`/`gamma` is validated here so
    an `"ipv"` spec cannot silently carry a live persona term.
channel, dm_cap, talk_rounds : str, int, int
    The communication affordances (design.md §3.2, §3.4).
disclose_public_facts : bool
    The linkage-principle switch [milgrom_weber1982]: whether the stage publishes extra public information.
ring : RingSpec | None
    An instructed/designated ring, or `None` (the committed cells).
framing : str
    `"datacenter"` (default) or `"neutral"` — a prompt-surface flag carried on the spec so the
    analysis can never pool the two by accident.
meta : dict
    Anything scenario- or generator-private (provenance, bank position, difficulty tags).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `item_slots` | tuple[[ItemSlot](ItemSlot.md), ...] | *required* |  |
| `attr_names` | `tuple[str, ...]` | *required* |  |
| `bidders` | tuple[[BidderSpec](BidderSpec.md), ...] | *required* |  |
| `horizon` | `int` | *required* |  |
| `stages` | tuple[[StageDraw](StageDraw.md), ...] | *required* |  |
| `mechanism` | [Mechanism](Mechanism.md) | *required* |  |
| `beta` | `float` | `DEFAULT_BETA` |  |
| `sigma_z` | `float` | `DEFAULT_SIGMA_Z` |  |
| `sigma_eps` | `float` | `DEFAULT_SIGMA_EPS` |  |
| `sigma_nu` | `float` | `DEFAULT_SIGMA_NU` |  |
| `value_structure` | `str` | `'apv'` |  |
| `channel` | `str` | `'silent'` |  |
| `dm_cap` | `int` | `DEFAULT_DM_CAP` |  |
| `talk_rounds` | `int` | `DEFAULT_TALK_ROUNDS` |  |
| `disclose_public_facts` | `bool` | `False` |  |
| `ring` | [RingSpec](RingSpec.md) \| None | `None` |  |
| `framing` | `str` | `'datacenter'` |  |
| `meta` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `K` | `int` | Number of public attribute dimensions. |
| `attr_names` | `tuple[str, ...]` |  |
| `attrs` | `np.ndarray` | The `(n_bidders, K)` public attribute matrix `a`. |
| `beta` | `float` |  |
| `bidders` | tuple[[BidderSpec](BidderSpec.md), ...] |  |
| `capacities` | `tuple[int, ...]` | Per-seat capacity `k_i` (max lots won per stage). |
| `channel` | `str` |  |
| `decays` | `tuple[float, ...]` | Per-seat diminishing-returns factor `d_i`. |
| `disclose_public_facts` | `bool` |  |
| `dm_cap` | `int` |  |
| `framing` | `str` |  |
| `gammas` | `tuple[float, ...]` | Per-seat resale weight `gamma_i` (all zero outside INTERDEP). |
| `horizon` | `int` |  |
| `item_slots` | tuple[[ItemSlot](ItemSlot.md), ...] |  |
| `loadings` | `np.ndarray` | The `(n_items, K)` public loading matrix `w`. |
| `mechanism` | [Mechanism](Mechanism.md) |  |
| `meta` | `dict` |  |
| `n_bidders` | `int` | Number of seats (always :data:`N_BIDDERS`). |
| `n_items` | `int` | Number of distinct lots per stage. |
| `ring` | [RingSpec](RingSpec.md) \| None |  |
| `sigma_eps` | `float` |  |
| `sigma_nu` | `float` |  |
| `sigma_z` | `float` |  |
| `stages` | tuple[[StageDraw](StageDraw.md), ...] |  |
| `synergy_rates` | `tuple[float, ...]` | Per-seat complementarity rate `c_i`. |
| `talk_rounds` | `int` |  |
| `value_structure` | `str` |  |

## Methods {#methods}

## `attribute_score` {#attribute_score}

```python
attribute_score(self) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L595-L600)

The public affinity matrix `(n_bidders, n_items)` of `a_i . w_j` — everything a rival holding only public facts knows about the shape of `i`'s valuation curve (design.md §2.2).

Zero under IPV
only in effect, not in value: the matrix is still computable, but `beta = 0` makes it carry no
information about realized values, which is what the IPV seat cards say.

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'AuctionSpec'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L629-L652)

Rebuild an :class:`AuctionSpec` from :meth:`to_json` output — an exact round-trip, so a stored instance replays the SAME auction.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `prefix` {#prefix}

```python
prefix(self, horizon: int) -> 'AuctionSpec'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L602-L608)

This spec truncated to its first `horizon` stages — how a `T = 6` or `T = 8` cell consumes a bank instance that carries :data:`BANK_STAGES` draws (design.md §7.1).

A strict prefix, so the
long-horizon cell is an extension of the committed cells on identical instances.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `horizon` | `int` | *required* |  |

## `stage` {#stage}

```python
stage(self, t: int) -> StageDraw
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L589-L593)

The stage-`t` draw, `t` 1-indexed as in design.md §3.1.

Raises `IndexError` past the horizon.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `t` | `int` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L610-L627)

JSON-ready dict of the whole spec (drops straight into `Instance.payload`).
