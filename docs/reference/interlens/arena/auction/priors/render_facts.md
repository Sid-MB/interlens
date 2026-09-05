# `render_facts`

Render fact values to prose lines through :data:`FACT_RENDERERS`, in `keys` order (default: the dict's own order).

```python
render_facts(facts: dict, keys: tuple[str, ...] | None = None) -> list[str]
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L322-L333)

A key with no registered renderer falls back to `"<key>: <value>"`, so a bare harness
and the tests work before the scenario lane connects its templates.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `facts` | `dict` | *required* |  |
| `keys` | `tuple[str, ...] \| None` | `None` |  |
