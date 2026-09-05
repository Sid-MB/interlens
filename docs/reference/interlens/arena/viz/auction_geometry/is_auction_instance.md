# `is_auction_instance`

Whether a stored `Instance` dict carries an auction spec — the discriminator the viz layer branches on.

```python
is_auction_instance(instance: dict | None) -> bool
```

Defined in [`interlens.arena.viz.auction_geometry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L78-L91)

Checks the payload's shape rather than the record's `scenario` field, because a bank instance is
generated once and consumed by cells that override the mechanism, and because a comparison payload may
carry an instance whose scenario string was never written.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | `dict \| None` | *required* |  |
