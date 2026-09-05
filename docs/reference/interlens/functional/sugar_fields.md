# `sugar_fields`

Class decorator declaring copy-on-write dot-modifier sugar for `names`.

```python
sugar_fields(*names: str = ())
```

Defined in [`interlens.functional`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/functional.py#L71-L83)

Each `name` becomes an accessor
(`obj.name()` reads, `obj.name(v)` returns a modified copy) backed by the dataclass field `_name`. The
public names are also accepted by `set(**changes)`; the underscored storage names are hidden from it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `names` | `str` | `()` |  |
