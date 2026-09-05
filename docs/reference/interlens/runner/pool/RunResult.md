# `RunResult`

Outcome of one job: the finished `conversation` (weightless participants + completed transcript), its `transcript` and (serializable) `analysis`, or an `error` string if it failed.

```python
RunResult(
	job_id: str,
	conversation: object = None,
	transcript: object = None,
	analysis: object = None,
	error: str | None = None,
	device: str | None = None,
)
```

Defined in [`interlens.runner.pool`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/pool.py#L33-L52)

`conversation` is the
object to `sample()`/inspect after a rollout (the source recipe is never mutated).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `job_id` | `str` | *required* |  |
| `conversation` | `object` | `None` |  |
| `transcript` | `object` | `None` |  |
| `analysis` | `object` | `None` |  |
| `error` | `str \| None` | `None` |  |
| `device` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `analysis` | `object` |  |
| `conversation` | `object` |  |
| `device` | `str \| None` |  |
| `error` | `str \| None` |  |
| `job_id` | `str` |  |
| `tokens_generated` | `int` | Total generated tokens in this conversation (summed from each turn's `metadata['n_tokens']`) — the realized compute, for verifying matched-compute comparisons. 0 if the job failed. |
| `transcript` | `object` |  |
