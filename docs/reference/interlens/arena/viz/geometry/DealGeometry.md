# `DealGeometry`

One deal's full record: where it plots, and how every party feels about it.

```python
DealGeometry(
	index: int,
	named: dict[str, str],
	u: list[float],
	s: list[float],
	xn: list[float],
	wx: float,
	wy: float,
	pareto: bool,
	ir: bool,
	feasible: bool,
	d_frontier: float,
)
```

Defined in [`interlens.arena.viz.geometry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L89-L122)

`index` is the deal's row in the utility matrix (and its position in `DealSpace.enumerate` order);
`u`/`s`/`xn` are the per-party utility, raw surplus, and normalized surplus vectors; `wx`/`wy` the
embedding coordinates; `pareto`/`ir`/`feasible` its membership flags (Pareto-optimal, individually
rational for every party, and passing this game's full agreement rule including veto/min-accept/structural
constraints); `pareto_ir` the conjunction `pareto and ir` — efficient AND acceptable to everyone, i.e. on
the frontier a rational table could actually reach; `d_frontier` its normalized-surplus distance below the
UNCONSTRAINED frontier (0 iff Pareto-optimal, so a deal below somebody's threshold can still read 0).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `index` | `int` | *required* |  |
| `named` | `dict[str, str]` | *required* |  |
| `u` | `list[float]` | *required* |  |
| `s` | `list[float]` | *required* |  |
| `xn` | `list[float]` | *required* |  |
| `wx` | `float` | *required* |  |
| `wy` | `float` | *required* |  |
| `pareto` | `bool` | *required* |  |
| `ir` | `bool` | *required* |  |
| `feasible` | `bool` | *required* |  |
| `d_frontier` | `float` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `d_frontier` | `float` |  |
| `feasible` | `bool` |  |
| `index` | `int` |  |
| `ir` | `bool` |  |
| `named` | `dict[str, str]` |  |
| `pareto` | `bool` |  |
| `pareto_ir` | `bool` | Efficient *and* individually rational — derived, never stored, so it cannot drift from its parts. |
| `s` | `list[float]` |  |
| `u` | `list[float]` |  |
| `wx` | `float` |  |
| `wy` | `float` |  |
| `xn` | `list[float]` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L118-L122)
