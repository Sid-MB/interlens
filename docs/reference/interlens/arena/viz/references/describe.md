# `describe`

Everything a renderer needs about one reference, flattened into one dict.

```python
describe(name: str) -> dict
```

Defined in [`interlens.arena.viz.references`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/references.py#L175-L208)

Returns `{}` for a name that is not a known decision reference — a generic scored oracle keeps rendering
through the page's older, name-agnostic path rather than being described wrongly. Otherwise the keys are
`role` (the canonical name), `label`, `short`, `information`, `information_detail`, `objective`,
`objective_name`, `value_label`, `unit`, `value_basis`, `comparable_across_information`,
`gap_label`, `objective_note`, and `legacy`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
