# `TokenEstimate`

Exponentially weighted per-request token consumption, used to project the token buckets forward between header reports.

```python
TokenEstimate(
	input_tokens: float = 8000.0,
	output_tokens: float = 2000.0,
	weight: float = 0.2,
)
```

Defined in [`interlens.participant.governor`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L96-L116)

Seeded high (a fresh run has no observations and should under- rather than over-admit) and
updated from every response that reports usage.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `input_tokens` | `float` | `8000.0` |  |
| `output_tokens` | `float` | `2000.0` |  |
| `weight` | `float` | `0.2` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `input_tokens` | `float` |  |
| `output_tokens` | `float` |  |
| `weight` | `float` |  |

## Methods {#methods}

## `observe` {#observe}

```python
observe(self, tokens_in: int, tokens_out: int) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L106-L110)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tokens_in` | `int` | *required* |  |
| `tokens_out` | `int` | *required* |  |

## `per_bucket` {#per_bucket}

```python
per_bucket(self) -> dict[str, float]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L112-L116)

The estimated consumption one admitted request charges to each token bucket.

The undifferentiated
`tokens` bucket (reported on some plans instead of the split pair) is charged the sum.
