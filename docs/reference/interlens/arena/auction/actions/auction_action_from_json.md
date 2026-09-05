# `auction_action_from_json`

Reconstruct a typed auction :class:`Action` from its stored dict — the inverse of `to_json`.

```python
auction_action_from_json(d: dict) -> Action
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L225-L250)

Raises
`ValueError` for a dict that does not name an auction action kind.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |
