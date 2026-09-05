# `read_state_block`

The latest `auction_state` block in a view.

```python
read_state_block(view) -> dict
```

Defined in [`interlens.arena.scenarios.auction_policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_policy.py#L61-L70)

Latest wins, so a retry prompt cannot resurrect a stale
round.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `view` |  | *required* |  |
