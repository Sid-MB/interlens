# `register_fact_renderer`

Register the prose renderer for one fact key.

```python
register_fact_renderer(
	key: str,
	fn: 'Callable[[object], str]',
	*,
	overwrite: bool = False,
) -> None
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L313-L319)

Re-registering without `overwrite=True` is an error, so
two prompt variants cannot silently share a key (the same fail-fast rule as
`negotiation/sheets.py::register_constraint`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `key` | `str` | *required* |  |
| `fn` | `'Callable[[object], str]'` | *required* |  |
| `overwrite` | `bool` | `False` |  |
