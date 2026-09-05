# `DatasetField`

A placeholder for `row[name]` in a templated field, created by :func:`dataset_field`.

```python
DatasetField(name: str)
```

Defined in [`interlens.templating`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/templating.py#L45-L50)

Frozen + tiny so it
serializes and pickles trivially across a spawn boundary.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` | `str` |  |
