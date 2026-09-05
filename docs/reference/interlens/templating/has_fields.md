# `has_fields`

Whether `value` depends on the dataset row (contains a `DatasetField`, a callable, or a t-string).

```python
has_fields(value) -> bool
```

Defined in [`interlens.templating`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/templating.py#L59-L68)

A
conversation whose framing has no fields can be run directly; one that has them must be expanded over data.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `value` |  | *required* |  |
