# `StageDraw`

One stage's realized draws — everything that redraws from the same persona priors (design.md §2.4).

```python
StageDraw(
	stage: int,
	base_values: tuple[int, ...],
	z: tuple[float, ...],
	eps: tuple[tuple[float, ...], ...],
	values: tuple[tuple[int, ...], ...],
	budgets: tuple[int, ...],
	synergy_target: tuple[tuple[int, ...] | None, ...],
	tie_break: tuple[int, ...],
	clock_ceiling: int,
	resale: tuple[int, ...] | None = None,
	signals: tuple[tuple[int, ...], ...] | None = None,
)
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L360-L438)

Attributes
----------
stage : int
    1-indexed stage number within the episode.
base_values : tuple[int, ...]
    `B_jt`, the PUBLIC catalogue base value per slot for this stage.
z : tuple[float, ...]
    `z_it`, the PRIVATE bidder-level shifter (its SD `sigma_z` is public).
eps : tuple[tuple[float, ...], ...]
    `eps_ijt`, the PRIVATE per-(bidder, slot) idiosyncrasy (its SD `sigma_eps` is public).
values : tuple[tuple[int, ...], ...]
    `v_ijt`, the PRIVATE realized whole-number valuations — the equation of design.md §2.2 evaluated and
    rounded.
budgets : tuple[int, ...]
    PRIVATE whole-number per-stage budget, replenished each stage (never carried; design.md §2.4).
synergy_target : tuple[tuple[int, ...] | None, ...]
    PRIVATE synergy target SET per bidder (`None` for a bidder with `synergy_rate == 0`). Its size
    follows the lot count; its identity redraws each stage.
resale : tuple[int, ...] | None
    `R_jt`, the common resale value — known to NOBODY, INTERDEP only.
signals : tuple[tuple[int, ...], ...] | None
    PRIVATE noisy resale signals `R_jt + nu_ijt` (`sigma_nu` public), INTERDEP only.
tie_break : tuple[int, ...]
    Seeded seat permutation, announced before bidding; ties are resolved by position in this list.
clock_ceiling : int
    The price at which a clock family's round cap binds — set above the maximum realized valuation so the
    ceiling is reachable only by a bidder bidding above every value in the stage.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int` | *required* |  |
| `base_values` | `tuple[int, ...]` | *required* |  |
| `z` | `tuple[float, ...]` | *required* |  |
| `eps` | `tuple[tuple[float, ...], ...]` | *required* |  |
| `values` | `tuple[tuple[int, ...], ...]` | *required* |  |
| `budgets` | `tuple[int, ...]` | *required* |  |
| `synergy_target` | `tuple[tuple[int, ...] \| None, ...]` | *required* |  |
| `tie_break` | `tuple[int, ...]` | *required* |  |
| `clock_ceiling` | `int` | *required* |  |
| `resale` | `tuple[int, ...] \| None` | `None` |  |
| `signals` | `tuple[tuple[int, ...], ...] \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `base_values` | `tuple[int, ...]` |  |
| `budgets` | `tuple[int, ...]` |  |
| `clock_ceiling` | `int` |  |
| `eps` | `tuple[tuple[float, ...], ...]` |  |
| `resale` | `tuple[int, ...] \| None` |  |
| `signals` | `tuple[tuple[int, ...], ...] \| None` |  |
| `stage` | `int` |  |
| `synergy_target` | `tuple[tuple[int, ...] \| None, ...]` |  |
| `tie_break` | `tuple[int, ...]` |  |
| `value_array` | `np.ndarray` | The realized valuations as an `(n_bidders, n_items)` integer array — the workhorse every allocation, benchmark, and metric consumes. |
| `values` | `tuple[tuple[int, ...], ...]` |  |
| `z` | `tuple[float, ...]` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'StageDraw'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L421-L438)

Rebuild a :class:`StageDraw` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L411-L419)

JSON-ready dict (nested tuples become nested lists; `None` targets are preserved).
