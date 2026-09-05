# `advice_summary`

This episode's compliance record: how many turns were advised, how many followed, on which rung.

```python
advice_summary(turns: dict[str, dict]) -> dict
```

Defined in [`interlens.arena.viz.advice`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/advice.py#L135-L160)

`n_followed` counts turns whose stored verdict is a match; `n_overridden` counts the explicit non-matches
only. A turn whose verdict is missing (a trace that failed to join its sidecar) is in neither, and
`n_unverdicted` says so rather than letting an unknown fall into the compliant column.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `turns` | `dict[str, dict]` | *required* |  |
