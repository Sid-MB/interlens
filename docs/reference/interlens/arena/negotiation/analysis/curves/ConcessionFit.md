# `ConcessionFit`

Fitted `y(x) = d + b*tanh(a*x - c)` on normalized turn-fraction x∈[0,1] and normalized concession y∈[0,1], plus the derived shape metrics.

```python
ConcessionFit(
	a: float,
	b: float,
	c: float,
	d: float,
	tau: float,
	cri: float,
	rmse: float,
	n: int,
)
```

Defined in [`interlens.arena.negotiation.analysis.curves`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/curves.py#L36-L52)

`n` is the number of offers fitted; `rmse` the fit residual
(a large rmse means the tanh family does not describe this trajectory — read τ/CRI with care).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `a` | `float` | *required* |  |
| `b` | `float` | *required* |  |
| `c` | `float` | *required* |  |
| `d` | `float` | *required* |  |
| `tau` | `float` | *required* |  |
| `cri` | `float` | *required* |  |
| `rmse` | `float` | *required* |  |
| `n` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `a` | `float` |  |
| `b` | `float` |  |
| `c` | `float` |  |
| `cri` | `float` |  |
| `d` | `float` |  |
| `n` | `int` |  |
| `rmse` | `float` |  |
| `tau` | `float` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/curves.py#L51-L52)
