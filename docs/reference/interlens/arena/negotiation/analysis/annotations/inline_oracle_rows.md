# `inline_oracle_rows`

The episode's INLINE oracle annotation rows in `round_checkpoints` — the `OracleRecord.to_json()` dicts, identified by a `"verdict"` key (forked provisional-probe rows have no verdict and are excluded).

```python
inline_oracle_rows(episode: dict) -> list[dict]
```

Defined in [`interlens.arena.negotiation.analysis.annotations`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L157-L160)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
