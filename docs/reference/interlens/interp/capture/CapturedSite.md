# `CapturedSite`

One activation captured by `capture_activations`: the `tensor` (`[seq, d_model]`) at a given `layer` and `site`.

```python
CapturedSite()
```

Defined in [`interlens.interp.capture`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/capture.py#L30-L37)

**Inherits from:** `NamedTuple`

A lightweight typed row (unpacks like the old `(layer, site, tensor)` tuple) that
the participant folds into a fully-tagged `ActivationRecord`.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `layer` | `int` |  |
| `site` | `Site` |  |
| `tensor` | `torch.Tensor` |  |
