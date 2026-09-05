# `GameGeometry`

The exact, fully-enumerated geometry of one negotiation instance, ready to plot.

```python
GameGeometry(
	game: GameSpec,
	solutions: dict | None = None,
	analysis: dict | None = None,
	*,
	ceiling: float | None = None,
	floor: float | None = None,
)
```

Defined in [`interlens.arena.viz.geometry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L125-L367)

Built once per instance and shared by every episode played on it (both sides of a seat-swap comparison read
the same object, so the two trajectories are guaranteed to be drawn against one identical frontier).

Attributes
----------
game : GameSpec
    The reconstructed game (deal space, private sheets, thresholds, protocol knobs).
U, X, Xn : numpy.ndarray
    The `|D| x n` utility, raw-surplus, and normalized-surplus tables.
wx, wy : numpy.ndarray
    The `(|D|,)` embedding coordinates (mean and min normalized surplus).
pareto, ir, feasible : numpy.ndarray
    Boolean `(|D|,)` membership masks.
pareto_ir : numpy.ndarray
    `pareto & ir` — the IR-feasible frontier: efficient AND above every party's threshold. This is the
    frontier the charts ring and shade; `pareto & ~ir` deals are efficient but unreachable and are drawn
    distinctly rather than dropped.
solutions : dict
    `{concept: SolutionPoint.to_json()}` for every concept in
    :data:`~interlens.arena.viz.geometry.CONCEPT_LABELS` plus any extra the stored analysis carried.
party_best : list[int]
    Per party, the deal index of its individually-best deal on the frontier — the "if this party could
    dictate the outcome (subject to everyone clearing their threshold and the deal being efficient)" point.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameSpec](../../negotiation/sheets/GameSpec.md) | *required* |  |
| `solutions` | `dict \| None` | `None` |  |
| `analysis` | `dict \| None` | `None` |  |
| `ceiling` | `float \| None` | `None` |  |
| `floor` | `float \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `U` |  |  |
| `X` |  |  |
| `Xn` |  |  |
| `analysis` |  |  |
| `feasible` |  |  |
| `game` |  |  |
| `ir` |  |  |
| `n_deals` | `int` | Deal-space size `\|D\|`. |
| `n_parties` | `int` | Number of parties `n`. |
| `pareto` |  |  |
| `pareto_ir` |  |  |
| `parties` | `list[str]` | Score-sheet party ids in seat order (`"P0"`, `"P1"`, ... — the seat *personas* live on the episode, not the game). |
| `party_best` |  |  |
| `solutions` |  |  |
| `solutions_source` |  |  |
| `tau` |  |  |
| `wx` |  |  |
| `wy` |  |  |

## Methods {#methods}

## `at` {#at}

```python
at(self, index: int) -> DealGeometry
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L278-L288)

The full :class:`DealGeometry` record for a deal index.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `index` | `int` | *required* |  |

## `deal_index` {#deal_index}

```python
deal_index(self, named: Any) -> int | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L262-L276)

The deal index of a `{issue_name: option_label}` proposal (tolerant of case/whitespace, via `DealSpace.parse`), or `None` if it is missing, malformed, or names an unknown option — which is exactly the case for a model's invalid proposal, so the caller gets `None` instead of an exception.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `named` | `Any` | *required* |  |

## `envelope` {#envelope}

```python
envelope(self, mask: np.ndarray | None = None) -> list[list[float]]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L298-L311)

The efficient envelope of the frontier IN THE 2-D EMBEDDING: the staircase of frontier deals that are non-dominated on `(joint welfare, min surplus)` themselves, ordered left to right.

`mask` selects which frontier is traced and defaults to :attr:`pareto` (the unconstrained one). Pass
:attr:`pareto_ir` for the envelope of the deals that could actually close; the charts draw that one as
the shaded region and keep the unconstrained staircase as a separate, visibly different line.

The projection is lossy, so a deal on the true `R^n` frontier can sit strictly inside this envelope —
it is efficient overall while being beaten on both plotted summaries by some other efficient deal. The
envelope is therefore drawn as the outer boundary of the achievable region and never used to decide
whether a deal is Pareto-optimal; that always comes from :attr:`pareto`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `mask` | `np.ndarray \| None` | `None` |  |

## `from_instance` {#from_instance}

```python
from_instance(instance: dict) -> 'GameGeometry | None'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L204-L220)

The geometry of a stored `Instance` dict, or `None` if its payload is not a scorable game (so a caller can render a non-negotiation scenario's episode without the game panel instead of crashing).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | `dict` | *required* |  |

## `solution_index` {#solution_index}

```python
solution_index(self, concept: str) -> int | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L257-L260)

The deal index of a solution concept, or `None` if the instance carries no such concept.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `concept` | `str` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L314-L367)

The whole geometry as one JSON payload for the browser: the game description, the per-deal tables (all `|D|` deals, so every point in the cloud is hoverable without a round trip), and the reference marks.

## `welfare_of` {#welfare_of}

```python
welfare_of(self, index: int) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L290-L296)

The welfare scalars of one deal, in raw surplus units: `usw` (sum), `esw` (min), `nsw_geomean` (the readable geometric-mean form of the Nash product), and the count of parties left below threshold.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `index` | `int` | *required* |  |
