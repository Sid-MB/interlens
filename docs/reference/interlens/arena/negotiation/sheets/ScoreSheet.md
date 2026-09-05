# `ScoreSheet`

One party's private additive score sheet.

```python
ScoreSheet(agent: str, values: tuple[tuple[float, ...], ...], threshold: float)
```

Defined in [`interlens.arena.negotiation.sheets`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L77-L133)

`values[j]` is the tuple of per-option values for issue `j` (same length as that issue's options);
`threshold` is the party's private acceptance minimum `tau_i` (its BATNA). Utility is the sum of the
chosen options' values; surplus is utility minus threshold. Frozen/hashable so a tuple of sheets can key a
cached utility matrix.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agent` | `str` | *required* |  |
| `values` | `tuple[tuple[float, ...], ...]` | *required* |  |
| `threshold` | `float` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `agent` | `str` |  |
| `max_utility` | `float` | Best attainable utility (pick each issue's highest-valued option). |
| `min_utility` | `float` | Worst attainable utility (pick each issue's lowest-valued option). |
| `n_issues` | `int` | Number of issues this sheet scores. |
| `threshold` | `float` |  |
| `values` | `tuple[tuple[float, ...], ...]` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'ScoreSheet'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L130-L133)

Rebuild a `ScoreSheet` from :meth:`to_json` output (lists -> tuples).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `rescaled` {#rescaled}

```python
rescaled(self, a: float, c: float = 0.0) -> 'ScoreSheet'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L113-L124)

This sheet under the positive affine transform of the *utility function* `u -> a*u + c` with the threshold moved the same way (`tau -> a*tau + c`).

Requires `a > 0`. Because the disagreement point
moves with the scale, every surplus obeys `x -> a*x` exactly; scale-invariant concepts (NBS, KS) are
unchanged, non-invariant ones (utilitarian, egalitarian) generally are not -- the property the tests
exercise. The additive constant `c` is realized on the additive sheet by adding it to a single issue's
options (issue 0), so that the *total* utility shifts by `c` exactly once (not once per issue).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `a` | `float` | *required* |  |
| `c` | `float` | `0.0` |  |

## `surplus` {#surplus}

```python
surplus(self, deal: Deal) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L94-L96)

Surplus `x(d) = u(d) - threshold` -- positive iff the deal clears this party's BATNA.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L126-L128)

JSON-ready dict (values as nested lists).

## `utility` {#utility}

```python
utility(self, deal: Deal) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L90-L92)

Additive utility `u(d) = sum_j values[j][d_j]` of a deal.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |
