# `LogLogRegret`

Log–log regression `log R_t = b0 log t + b1` of cumulative regret (Park §3.1).

```python
LogLogRegret(beta0: float, intercept: float, r2: float, sublinear: bool, n_points: int)
```

Defined in [`interlens.arena.negotiation.analysis.curves`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/curves.py#L182-L195)

`b0 < 1` ⇒ sublinear
cumulative regret ⇒ no-regret. `r2` is the fit quality; `n_points` the turns with positive cumulative
regret (log is undefined at zero, so leading zero-regret turns are dropped).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `beta0` | `float` | *required* |  |
| `intercept` | `float` | *required* |  |
| `r2` | `float` | *required* |  |
| `sublinear` | `bool` | *required* |  |
| `n_points` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `beta0` | `float` |  |
| `intercept` | `float` |  |
| `n_points` | `int` |  |
| `r2` | `float` |  |
| `sublinear` | `bool` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/curves.py#L194-L195)
