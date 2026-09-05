# `TurnAnnotation`

One turn's oracle annotation.

```python
TurnAnnotation(
	turn_idx: int,
	round: int,
	seat: str,
	oracle: dict[str, dict] = dict(),
	regret: float | None = None,
	flags: list[str] = list(),
	cf_regret: float | None = None,
	cot_first_divergent_step: int | None = None,
	oracle_belief: Any = None,
	stated_belief: Any = None,
	counterfactuals: dict[str, dict] = dict(),
)
```

Defined in [`interlens.arena.negotiation.analysis.annotations`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L32-L64)

`oracle` maps an oracle name to its scored verdict dict. `counterfactuals` stores named decision
references such as `rational_private` and `oracle_omniscient`; each value may carry `action`, `deal` or
`deal_index`, `value`, and `information`. Keeping decision references separate from scored oracle
verdicts lets a visualizer compare the action actually taken with both an information-feasible policy and a
privileged hindsight optimum without pretending that they share an information set. Older annotation files
omit the field and deserialize to an empty mapping.

`regret` is the headline per-turn surplus loss from the primary value oracle, while `flags` are the
taxonomy row identifiers that fired for this turn.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `turn_idx` | `int` | *required* |  |
| `round` | `int` | *required* |  |
| `seat` | `str` | *required* |  |
| `oracle` | `dict[str, dict]` | `dict()` |  |
| `regret` | `float \| None` | `None` |  |
| `flags` | `list[str]` | `list()` |  |
| `cf_regret` | `float \| None` | `None` |  |
| `cot_first_divergent_step` | `int \| None` | `None` |  |
| `oracle_belief` | `Any` | `None` |  |
| `stated_belief` | `Any` | `None` |  |
| `counterfactuals` | `dict[str, dict]` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `cf_regret` | `float \| None` |  |
| `cot_first_divergent_step` | `int \| None` |  |
| `counterfactuals` | `dict[str, dict]` |  |
| `flags` | `list[str]` |  |
| `oracle` | `dict[str, dict]` |  |
| `oracle_belief` | `Any` |  |
| `regret` | `float \| None` |  |
| `round` | `int` |  |
| `seat` | `str` |  |
| `stated_belief` | `Any` |  |
| `turn_idx` | `int` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'TurnAnnotation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L62-L64)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L59-L60)
