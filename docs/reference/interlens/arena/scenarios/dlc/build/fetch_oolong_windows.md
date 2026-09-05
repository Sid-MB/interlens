# `fetch_oolong_windows`

`window_id -> {'plain': str, 'labeled': str}` for trec_coarse windows at `context_len`.

```python
fetch_oolong_windows(context_len: int, revision: str | None = None) -> dict[int, dict]
```

Defined in [`interlens.arena.scenarios.dlc.build`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/build.py#L199-L210)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `context_len` | `int` | *required* |  |
| `revision` | `str \| None` | `None` |  |
