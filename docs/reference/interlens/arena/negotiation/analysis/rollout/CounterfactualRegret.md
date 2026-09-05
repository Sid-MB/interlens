# `CounterfactualRegret`

Δ expected surplus between the oracle action and the model action for the acting `agent`: positive = the oracle's action leads to more surplus (a real divergence), 0 = the model's action was as good.

```python
CounterfactualRegret(
	agent: str,
	surplus_model: float,
	surplus_oracle: float,
	delta: float,
	k: int,
)
```

Defined in [`interlens.arena.negotiation.analysis.rollout`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L64-L77)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agent` | `str` | *required* |  |
| `surplus_model` | `float` | *required* |  |
| `surplus_oracle` | `float` | *required* |  |
| `delta` | `float` | *required* |  |
| `k` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `agent` | `str` |  |
| `delta` | `float` |  |
| `k` | `int` |  |
| `surplus_model` | `float` |  |
| `surplus_oracle` | `float` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/rollout.py#L75-L77)
