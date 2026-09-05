# `GameSpec`

A complete negotiation game: the deal space, every party's private sheet, and the protocol knobs.

```python
GameSpec(
	space: DealSpace,
	sheets: tuple[ScoreSheet, ...],
	rounds: int = 4,
	info: str = 'full',
	chat: bool = True,
	proposer: int = 0,
	veto: int | list[int] | None = None,
	min_accept: int | None = None,
	discount: float = 1.0,
	breakdown_risk: float = 0.0,
	constraint: str | None = None,
	meta: dict = dict(),
)
```

Defined in [`interlens.arena.negotiation.sheets`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L136-L327)

Beyond `space`/`sheets` the fields carry the protocol arms: `rounds` (round-robin
rounds before a forced final), `info` (`"full"` = sheets common knowledge, `"private"` = only a prior
over types), `chat` (whether a public cheap-talk channel exists alongside formal moves), and the agreement
structure -- `proposer` seat (a rotating-proposer scenario may ignore this default), `veto` (one seat, a
list of seats, or `None` -- see :attr:`veto_seats`), and `min_accept` (how many parties must clear their
threshold; `None` = unanimity). Impatience knobs the equilibrium/acceptance oracles read as their single
source of truth: `discount` (per-round delta in (0, 1], 1.0 = none) and `breakdown_risk` (per-round
exogenous-breakdown probability in [0, 1), 0.0 = none). `meta` holds anything scenario-private (e.g.
generator provenance, issue-type labels). Serializes to/from a plain JSON dict for `Instance.payload`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `space` | [DealSpace](../space/DealSpace.md) | *required* |  |
| `sheets` | tuple[[ScoreSheet](ScoreSheet.md), ...] | *required* |  |
| `rounds` | `int` | `4` |  |
| `info` | `str` | `'full'` |  |
| `chat` | `bool` | `True` |  |
| `proposer` | `int` | `0` |  |
| `veto` | `int \| list[int] \| None` | `None` |  |
| `min_accept` | `int \| None` | `None` |  |
| `discount` | `float` | `1.0` |  |
| `breakdown_risk` | `float` | `0.0` |  |
| `constraint` | `str \| None` | `None` |  |
| `meta` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `agents` | `list[str]` | Party names in seat order. |
| `breakdown_risk` | `float` |  |
| `chat` | `bool` |  |
| `constraint` | `str \| None` |  |
| `discount` | `float` |  |
| `info` | `str` |  |
| `meta` | `dict` |  |
| `min_accept` | `int \| None` |  |
| `n_parties` | `int` | Number of parties `n`. |
| `proposer` | `int` |  |
| `rounds` | `int` |  |
| `sheets` | tuple[[ScoreSheet](ScoreSheet.md), ...] |  |
| `space` | [DealSpace](../space/DealSpace.md) |  |
| `thresholds` | `np.ndarray` | The reservation vector `tau` of shape `(n,)`. |
| `veto` | `int \| list[int] \| None` |  |
| `veto_seats` | `list[int]` | The veto seats as a list (`[]` if none): normalizes the `veto` field, which may be a single seat index, a list of seat indices, or `None`. |

## Methods {#methods}

## `constraint_fn` {#constraint_fn}

```python
constraint_fn(self) -> 'Callable[[Deal], bool] | None'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L278-L287)

This game's structural deal predicate, resolved from the `constraint` NAME via :data:`CONSTRAINTS`, or `None` when it declares none.

Raises `KeyError` for an unregistered name.

## `feasible` {#feasible}

```python
feasible(self, deal: Deal) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L289-L292)

Whether ONE deal may close under this game's agreement rule — the single-deal counterpart of :meth:`feasible_mask` (it indexes that mask, so the two can never disagree).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## `feasible_mask` {#feasible_mask}

```python
feasible_mask(self, U: np.ndarray | None = None) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L224-L244)

Boolean `(|D|,)` mask of deals that pass this game's agreement rule: the `proposer` clears its threshold, the `veto` seat (if any) clears its threshold, at least `min_accept` parties clear theirs (`min_accept=None` => all `n` => plain unanimity / the IR set), AND the deal satisfies this game's `constraint` (if it declares one).

Pass a precomputed `U` to avoid rebuilding it.

Because every exact solution concept, the oracles, and the scenario's surplus ceiling all read this
mask, a constraint declared here flows into all of them for free — it is the single definition of "may
this deal close?". :meth:`feasible` is the single-deal form of the same rule.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray \| None` | `None` |  |

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'GameSpec'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L311-L327)

Rebuild a `GameSpec` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `normalized_geometry` {#normalized_geometry}

```python
normalized_geometry(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L246-L276)

The game's scale-invariant surplus geometry, and the deal that attains its ceiling.

Each party is normalized by its own **capacity** `c_i = max_d x_i(d)` (its best surplus over the whole
deal space), giving `z_i = x_i / c_i`. The **ceiling** is `max` over the FEASIBLE set (whatever
:meth:`feasible_mask` admits) of `sum_i z_i`, and the **ceiling deal** is the argmax — ties broken by
the smallest enumeration index, so it is deterministic.

Returns `{"feasible", "capacities", "normalized_ceiling", "raw_ceiling", "ceiling_index",
"ceiling_deal"}`; `ceiling_index`/`ceiling_deal` are `None` when the game admits no feasible deal
or some party has zero capacity (a degenerate sheet), which is also when `normalized_ceiling` is 0.

This is the single definition of "the best deal on the table": `normalized_ceiling` is the denominator
of the scenario's `primary` score (so score 1.0 *is* the ceiling deal), and `ceiling_deal` is what an
experiment seeds when it wants the optimum already tabled.

## `surplus_matrix` {#surplus_matrix}

```python
surplus_matrix(self) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L220-L222)

The `|D| x n` surplus matrix `U - tau` for this game.

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L294-L309)

JSON-ready dict of the whole game (drops straight into `Instance.payload`).

## `utility_matrix` {#utility_matrix}

```python
utility_matrix(self) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L216-L218)

The `|D| x n` utility matrix for this game (see module-level :func:`utility_matrix`).
