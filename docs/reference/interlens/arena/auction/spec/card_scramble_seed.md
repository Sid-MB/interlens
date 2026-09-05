# `card_scramble_seed`

The frozen scramble seed for one bank instance, derived from its `instance_id`.

```python
card_scramble_seed(instance_id: str) -> int
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L818-L824)

A content hash rather than a counter, so the derangement is a property of the INSTANCE and is identical in
every rerun, on every machine, in any arm order -- the scramble is frozen with the bank even though it is
applied at cell time.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance_id` | `str` | *required* |  |
