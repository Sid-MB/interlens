# `CategoryResult`

Outcome of one taxonomy check on one episode.

```python
CategoryResult(
	category_id: int,
	name: str,
	tier: Tier,
	fired: bool,
	rate: float,
	evidence: list[dict] = list(),
	implemented: bool = True,
	note: str = '',
)
```

Defined in [`interlens.arena.negotiation.analysis.taxonomy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/taxonomy.py#L69-L85)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `category_id` | `int` | *required* |  |
| `name` | `str` | *required* |  |
| `tier` | [Tier](Tier.md) | *required* |  |
| `fired` | `bool` | *required* |  |
| `rate` | `float` | *required* |  |
| `evidence` | `list[dict]` | `list()` |  |
| `implemented` | `bool` | `True` |  |
| `note` | `str` | `''` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `category_id` | `int` |  |
| `evidence` | `list[dict]` |  |
| `fired` | `bool` |  |
| `implemented` | `bool` |  |
| `name` | `str` |  |
| `note` | `str` |  |
| `rate` | `float` |  |
| `tier` | [Tier](Tier.md) |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/taxonomy.py#L82-L85)
