# `policy_for`

The right computable bidder for a spec's mechanism and value structure.

```python
policy_for(spec, *, information: str = 'private') -> AuctionPolicy
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L681-L694)

`sealed_single`/`english` -> :class:`ConditionalBayesPolicy` (which reduces to bidding own value
under private values, so the rational and oracle seats coincide there exactly — G3);
`dutch` -> :class:`ConditionalBayesPolicy` as the stage-myopic best responder;
`uniform_price`/`clinching` -> :class:`DemandSchedulePolicy`; `saa` -> :class:`ConditionalBayesPolicy`
driving the ABC's capacity- and synergy-aware straightforward bidding.

This is the single dispatch point, so an arm never has to know which class it got.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `spec` |  | *required* |  |
| `information` | `str` | `'private'` |  |
