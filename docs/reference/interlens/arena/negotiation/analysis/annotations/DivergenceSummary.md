# `DivergenceSummary`

Episode-level roll-up of the turn annotations: the regret series and its aggregates, the divergence-point turns (regret above the noise threshold), and hard-flag counts by taxonomy row.

```python
DivergenceSummary(
	episode_id: str,
	model: str,
	arm: str,
	n_turns: int,
	n_flagged: int,
	regret_series: list[float],
	mean_regret: float,
	total_regret: float,
	divergence_turns: list[int],
	flag_counts: dict[str, int],
	outcome: dict = dict(),
)
```

Defined in [`interlens.arena.negotiation.analysis.annotations`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L67-L89)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode_id` | `str` | *required* |  |
| `model` | `str` | *required* |  |
| `arm` | `str` | *required* |  |
| `n_turns` | `int` | *required* |  |
| `n_flagged` | `int` | *required* |  |
| `regret_series` | `list[float]` | *required* |  |
| `mean_regret` | `float` | *required* |  |
| `total_regret` | `float` | *required* |  |
| `divergence_turns` | `list[int]` | *required* |  |
| `flag_counts` | `dict[str, int]` | *required* |  |
| `outcome` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `arm` | `str` |  |
| `divergence_turns` | `list[int]` |  |
| `episode_id` | `str` |  |
| `flag_counts` | `dict[str, int]` |  |
| `mean_regret` | `float` |  |
| `model` | `str` |  |
| `n_flagged` | `int` |  |
| `n_turns` | `int` |  |
| `outcome` | `dict` |  |
| `regret_series` | `list[float]` |  |
| `total_regret` | `float` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'DivergenceSummary'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L87-L89)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L84-L85)
