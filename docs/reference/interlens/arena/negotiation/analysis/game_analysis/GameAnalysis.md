# `GameAnalysis`

Solved-game bundle: surplus geometry + solution points + descriptors for one instance.

```python
GameAnalysis(
	n_agents: int,
	thresholds: tuple[float, ...],
	issues: list[tuple[str, list[str]]] = list(),
	sheets: list[list[list[float]]] | None = None,
	frontier: list[tuple[float, ...]] = list(),
	ir_deals: list[Deal] = list(),
	points: dict[str, tuple[float, ...] | None] = dict(),
	descriptors: dict[str, Any] = dict(),
	scale: tuple[float, ...] | None = None,
)
```

Defined in [`interlens.arena.negotiation.analysis.game_analysis`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/game_analysis.py#L43-L225)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_agents` | `int` | *required* |  |
| `thresholds` | `tuple[float, ...]` | *required* |  |
| `issues` | `list[tuple[str, list[str]]]` | `list()` |  |
| `sheets` | `list[list[list[float]]] \| None` | `None` |  |
| `frontier` | `list[tuple[float, ...]]` | `list()` |  |
| `ir_deals` | `list[Deal]` | `list()` |  |
| `points` | `dict[str, tuple[float, ...] \| None]` | `dict()` |  |
| `descriptors` | `dict[str, Any]` | `dict()` |  |
| `scale` | `tuple[float, ...] \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `descriptors` | `dict[str, Any]` |  |
| `frontier` | `list[tuple[float, ...]]` |  |
| `ir_deals` | `list[Deal]` |  |
| `issues` | `list[tuple[str, list[str]]]` |  |
| `n_agents` | `int` |  |
| `points` | `dict[str, tuple[float, ...] \| None]` |  |
| `scale` | `tuple[float, ...] \| None` |  |
| `sheets` | `list[list[list[float]]] \| None` |  |
| `thresholds` | `tuple[float, ...]` |  |

## Methods {#methods}

## `canonical_deal` {#canonical_deal}

```python
canonical_deal(self, deal_like: Any) -> Deal
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/game_analysis.py#L79-L101)

Map a proposed deal onto `tuple[int, ...]` (option index per issue).

Accepts an index tuple/list, or
a `{issue_name: option}` dict whose values are option names or indices. Raises `ValueError` on an
incomplete/unknown deal so a malformed proposal is a loud parse failure, not a silent mis-score.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal_like` | `Any` | *required* |  |

## `deal_frontier_distance` {#deal_frontier_distance}

```python
deal_frontier_distance(self, deal_like: Any) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/game_analysis.py#L117-L125)

Scale-invariant distance from a realized deal to the Pareto frontier (0 iff efficient).

Delegates to
the sibling `solutions.distance_to_frontier` (normalized-surplus space) for instances built via
`from_instance`; falls back to the Euclidean-on-surplus metric for hand-built fixtures.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal_like` | `Any` | *required* |  |

## `deal_point_distance` {#deal_point_distance}

```python
deal_point_distance(self, deal_like: Any, name: str) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/game_analysis.py#L127-L136)

Scale-invariant distance from a realized deal to a named solution point (`nbs`/`ks`/...).

Delegates to `solutions.distance_to_solution` for `from_instance` games, else Euclidean fallback.
`nan` if that point was not computed.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal_like` | `Any` | *required* |  |
| `name` | `str` | *required* |  |

## `distance_to_frontier` {#distance_to_frontier}

```python
distance_to_frontier(self, x: Sequence[float], *, normalized: bool = True) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/game_analysis.py#L104-L107)

Euclidean distance from surplus vector `x` to the Pareto frontier (0 if efficient).

With
`normalized` each coordinate is divided by that party's `scale` so parties are commensurable.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` | `Sequence[float]` | *required* |  |
| `normalized` | `bool` | `True` |  |

## `distance_to_point` {#distance_to_point}

```python
distance_to_point(
	self,
	x: Sequence[float],
	name: str,
	*,
	normalized: bool = True,
) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/game_analysis.py#L109-L115)

Euclidean distance from `x` to a named solution point (`nbs`/`ks`/...).

`nan` if that point
was not computed for this instance.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` | `Sequence[float]` | *required* |  |
| `name` | `str` | *required* |  |
| `normalized` | `bool` | `True` |  |

## `from_instance` {#from_instance}

```python
from_instance(cls, instance: Any) -> 'GameAnalysis'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/game_analysis.py#L143-L190)

Build from a stored `Instance` (or its `.to_json()` dict) whose `payload` is a `GameSpec`.

Delegates all solving to interlens' `solutions.py` (frontier via `pareto_mask`, points + descriptors
via `analyze`, read from `Instance.solution` when present, recomputed otherwise). interlens is imported
lazily so the pure metric math (and `from_sheets`) never require it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | `Any` | *required* |  |

## `from_sheets` {#from_sheets}

```python
from_sheets(
	cls,
	sheets: list[list[list[float]]],
	thresholds: Any,
	*,
	issues: list[tuple[str, list[str]]] | None = None,
	points: dict[str, tuple] | None = None,
) -> 'GameAnalysis'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/game_analysis.py#L192-L225)

Enumerate the deal space from raw score sheets and compute the frontier, IR set, welfare argmaxes, and descriptors.

A self-contained fallback and the tests' constructor — `solutions.py` is the
authority for the axiomatic NBS/KS/MNW points, which are only filled here if passed in `points`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sheets` | `list[list[list[float]]]` | *required* |  |
| `thresholds` | `Any` | *required* |  |
| `issues` | `list[tuple[str, list[str]]] \| None` | `None` |  |
| `points` | `dict[str, tuple] \| None` | `None` |  |

## `surplus` {#surplus}

```python
surplus(self, deal_like: Any) -> tuple[float, ...]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/game_analysis.py#L65-L77)

Surplus vector `(u_i(deal) - tau_i)_i` for a deal in any accepted form.

Computed from the score
sheets when present (exact for any deal), else looked up in the cached enumeration.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal_like` | `Any` | *required* |  |
