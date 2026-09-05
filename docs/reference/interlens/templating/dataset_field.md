# `dataset_field`

Reference a dataset column in a templated field: `shared_context=("Solve:\n\n", dataset_field("question"))` resolves `row["question"]` for each row at rollout expansion.

```python
dataset_field(name: str) -> DatasetField
```

Defined in [`interlens.templating`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/templating.py#L53-L56)

See the module docstring for all template forms.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
