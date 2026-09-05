# `resolve`

Resolve a template `value` against one dataset `row` (a mapping) to a concrete value.

```python
resolve(value, row: dict)
```

Defined in [`interlens.templating`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/templating.py#L71-L85)

Non-templated values (plain `str`/`None`/other) pass through unchanged; `DatasetField` → `row[name]`;
a callable → `value(row)`; a tuple/list → each part resolved and string-joined; a t-string → interpolated
with `DatasetField` interpolations pulled from the row.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `value` |  | *required* |  |
| `row` | `dict` | *required* |  |
