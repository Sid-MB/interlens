# `EpisodeAnnotation`

One episode's full divergence record: the summary plus every turn annotation.

```python
EpisodeAnnotation(
	episode_id: str,
	summary: DivergenceSummary,
	turns: list[TurnAnnotation] = list(),
)
```

Defined in [`interlens.arena.negotiation.analysis.annotations`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L92-L108)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode_id` | `str` | *required* |  |
| `summary` | [DivergenceSummary](DivergenceSummary.md) | *required* |  |
| `turns` | list[[TurnAnnotation](TurnAnnotation.md)] | `list()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `episode_id` | `str` |  |
| `summary` | [DivergenceSummary](DivergenceSummary.md) |  |
| `turns` | list[[TurnAnnotation](TurnAnnotation.md)] |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'EpisodeAnnotation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L104-L108)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L100-L102)
