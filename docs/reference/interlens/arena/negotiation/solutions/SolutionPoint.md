# `SolutionPoint`

One solution concept's chosen deal, resolved against a concrete game.

```python
SolutionPoint(
	concept: str,
	index: int,
	deal: Deal,
	named: dict[str, str],
	utilities: tuple[float, ...],
	surpluses: tuple[float, ...],
	ties: tuple[int, ...],
	note: str = '',
	scale_invariant: bool = True,
)
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L331-L356)

`index` is the deal's flat position (row in `U`), `deal` the option-index tuple, `named` its
human-readable form; `utilities` and `surpluses` are the per-party vectors at that deal; `ties` lists
every equally-optimal deal (>=1); `note` records fallbacks/caveats; `scale_invariant` flags whether the
concept is defensible across arbitrary private scales.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `concept` | `str` | *required* |  |
| `index` | `int` | *required* |  |
| `deal` | `Deal` | *required* |  |
| `named` | `dict[str, str]` | *required* |  |
| `utilities` | `tuple[float, ...]` | *required* |  |
| `surpluses` | `tuple[float, ...]` | *required* |  |
| `ties` | `tuple[int, ...]` | *required* |  |
| `note` | `str` | `''` |  |
| `scale_invariant` | `bool` | `True` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `concept` | `str` |  |
| `deal` | `Deal` |  |
| `index` | `int` |  |
| `named` | `dict[str, str]` |  |
| `note` | `str` |  |
| `scale_invariant` | `bool` |  |
| `surpluses` | `tuple[float, ...]` |  |
| `ties` | `tuple[int, ...]` |  |
| `utilities` | `tuple[float, ...]` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L350-L356)

JSON-ready dict.
