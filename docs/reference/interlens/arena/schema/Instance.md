# `Instance`

One generated problem instance, solver-verified at generation time.

```python
Instance(
	instance_id: str,
	scenario: str,
	level: int,
	seed: int,
	payload: dict,
	ceiling: float,
	floor: float,
	solution: dict,
)
```

Defined in [`interlens.arena.schema`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L67-L93)

`ceiling` is the best achievable primary score (computed exactly by the generator's solver), `floor` a
reference floor policy's score, and `solution` the exact optimum — never shown to models, used for
scoring and audits.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance_id` | `str` | *required* |  |
| `scenario` | `str` | *required* |  |
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |
| `payload` | `dict` | *required* |  |
| `ceiling` | `float` | *required* |  |
| `floor` | `float` | *required* |  |
| `solution` | `dict` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ceiling` | `float` |  |
| `floor` | `float` |  |
| `instance_id` | `str` |  |
| `level` | `int` |  |
| `payload` | `dict` |  |
| `scenario` | `str` |  |
| `seed` | `int` |  |
| `solution` | `dict` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'Instance'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L87-L93)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L84-L85)
