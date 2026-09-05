# `GameTables`

Precomputed dense tables for a game — built once, shared by every oracle so the `O(n*J*|D|)` utility pass is never duplicated.

```python
GameTables(
	deals: list[Deal],
	index: dict[Deal, int],
	deals_arr: np.ndarray,
	utility: np.ndarray,
	surplus: np.ndarray,
	thresholds: np.ndarray,
)
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L92-L155)

Attributes
----------
deals : list[Deal]
    The deal space in stable order.
index : dict[Deal, int]
    Inverse map `deal -> row`.
deals_arr : np.ndarray
    `(|D|, J)` int array of option indices.
utility : np.ndarray
    `(|D|, n)` per-deal per-agent utility.
surplus : np.ndarray
    `(|D|, n)` per-deal per-agent surplus `utility - threshold`.
thresholds : np.ndarray
    `(n,)` per-agent reservation thresholds.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deals` | `list[Deal]` | *required* |  |
| `index` | `dict[Deal, int]` | *required* |  |
| `deals_arr` | `np.ndarray` | *required* |  |
| `utility` | `np.ndarray` | *required* |  |
| `surplus` | `np.ndarray` | *required* |  |
| `thresholds` | `np.ndarray` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `deals` | `list[Deal]` |  |
| `deals_arr` | `np.ndarray` |  |
| `index` | `dict[Deal, int]` |  |
| `n_agents` | `int` |  |
| `n_deals` | `int` |  |
| `surplus` | `np.ndarray` |  |
| `thresholds` | `np.ndarray` |  |
| `utility` | `np.ndarray` |  |

## Methods {#methods}

## `from_game` {#from_game}

```python
from_game(cls, game) -> 'GameTables'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L128-L155)

Build tables from a `GameSpec`-like object exposing `.space` and `.sheets`.

Reuses the game's
own `utility_matrix()` when available (identical mixed-radix row order, no recomputation); otherwise
vectorizes utilities from each sheet's `.values` rows (single fancy-index per issue), falling back to
`sheet.utility` per deal. The single tables builder — there is no separate `build` entry point.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
