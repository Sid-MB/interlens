# `lot_blurb`

The prose description of a lot, generated from its loading vector through :data:`BLURB_PHRASES`.

```python
lot_blurb(loading, attr_names) -> str
```

Defined in [`interlens.arena.scenarios.auction_prompts`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_prompts.py#L164-L169)

The blurb and the numeric loading columns printed beside it are two renderings of one vector, so a bidder
reading either gets the same fit information and the two can never disagree.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `loading` |  | *required* |  |
| `attr_names` |  | *required* |  |
