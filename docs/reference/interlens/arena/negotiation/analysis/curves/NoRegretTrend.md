# `NoRegretTrend`

Mann–Kendall test for a *decreasing* trend in average regret `Regret_t / t` (Park §3.1 / Prop. 1).

```python
NoRegretTrend(
	n: int,
	mk_s: int,
	z: float,
	trend_pvalue: float,
	no_regret_evidence: bool,
	mean_avg_regret: float,
)
```

Defined in [`interlens.arena.negotiation.analysis.curves`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/curves.py#L130-L146)

`trend_pvalue` is the one-sided p-value for the decreasing alternative: small p ⇒ average regret is
significantly decreasing ⇒ evidence of no-regret behavior (`no_regret_evidence` at α=0.05). `mk_s` is the
Mann–Kendall statistic (negative = downward), `mean_avg_regret` the mean of `Regret_t/t`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n` | `int` | *required* |  |
| `mk_s` | `int` | *required* |  |
| `z` | `float` | *required* |  |
| `trend_pvalue` | `float` | *required* |  |
| `no_regret_evidence` | `bool` | *required* |  |
| `mean_avg_regret` | `float` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `mean_avg_regret` | `float` |  |
| `mk_s` | `int` |  |
| `n` | `int` |  |
| `no_regret_evidence` | `bool` |  |
| `trend_pvalue` | `float` |  |
| `z` | `float` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/curves.py#L145-L146)
