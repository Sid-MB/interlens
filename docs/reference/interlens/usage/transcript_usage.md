# `transcript_usage`

Aggregate the recorded usage of one transcript: total generated/input tokens, dollar cost, and a per-author breakdown — read from each committed message's metadata (`n_tokens` / `n_tokens_in` / `cost_usd`), the same source of truth `TokenBudget` and `CostBudget` use.

```python
transcript_usage(transcript: 'Transcript | Iterable[Message]') -> dict
```

Defined in [`interlens.usage`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L257-L275)

Turns without records
(seeded/moderator/scripted) contribute 0.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `transcript` | `'Transcript | Iterable[Message]'` | *required* |  |
