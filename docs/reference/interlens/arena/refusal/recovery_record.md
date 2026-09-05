# `recovery_record`

One turn's recovery record: `outcome` is `"recovered"` or `"terminal"`, `rung` the 1-based rung that cleared it (`None` when none did), `attempts` the rung names tried in order.

```python
recovery_record(outcome: str, rung: int | None, attempts: list[str]) -> dict
```

Defined in [`interlens.arena.refusal`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/refusal.py#L203-L207)

Reported as
`api_silence_recovered@rung_k` / `api_silence_terminal`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `outcome` | `str` | *required* |  |
| `rung` | `int \| None` | *required* |  |
| `attempts` | `list[str]` | *required* |  |
