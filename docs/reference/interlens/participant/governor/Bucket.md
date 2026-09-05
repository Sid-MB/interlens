# `Bucket`

One rate-limit bucket as last reported by the provider, plus the consumption the governor has admitted since that report.

```python
Bucket(
	limit: float,
	remaining: float,
	reset_monotonic: float,
	spent_since_report: float = 0.0,
)
```

Defined in [`interlens.participant.governor`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L73-L93)

`limit`/`remaining` are in the bucket's own units (requests, or tokens);
`reset_monotonic` is the refill deadline translated onto the local monotonic clock (the header is an
RFC3339 wall-clock timestamp, which is unusable for scheduling across clock skew).

Measured on this org (2026-08-15): an **un-depleted** bucket reports its reset as the current second, so a
healthy bucket's deadline is already in the past and only a drawn-down one names a future time.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `limit` | `float` | *required* |  |
| `remaining` | `float` | *required* |  |
| `reset_monotonic` | `float` | *required* |  |
| `spent_since_report` | `float` | `0.0` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `limit` | `float` |  |
| `remaining` | `float` |  |
| `reset_monotonic` | `float` |  |
| `spent_since_report` | `float` |  |

## Methods {#methods}

## `projected_remaining` {#projected_remaining}

```python
projected_remaining(self, now: float) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L88-L93)

Capacity expected to be left if every request admitted since the report consumes its estimate.

Past
the reset deadline the bucket has refilled, so the projection restarts from the full limit less what has
been admitted since (the conservative reading — the real refill may be more recent than the deadline).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `now` | `float` | *required* |  |
