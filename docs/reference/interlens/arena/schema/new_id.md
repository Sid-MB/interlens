# `new_id`

A fresh episode/instance id.

```python
new_id(prefix: str) -> str
```

Defined in [`interlens.arena.schema`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L61-L64)

Random (uuid4-based), deliberately NOT seed-derived: two runs of the same
seed produce identical payloads but distinct ids.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `prefix` | `str` | *required* |  |
