# `register_constraint`

Register a structural deal predicate under `name` for `GameSpec(constraint=name)`.

```python
register_constraint(name: str, predicate: 'Callable[[Deal], bool]') -> None
```

Defined in [`interlens.arena.negotiation.sheets`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L69-L74)

Re-registering the
same name is an error -- two games silently sharing a name would make a stored instance ambiguous.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `predicate` | `'Callable[[Deal], bool]'` | *required* |  |
