# `allocation_strip`

One bar per lot per stage: every seat's private valuation as a tick, the clearing price as the tau-line.

```python
allocation_strip(auction: dict, payload: dict) -> str
```

Defined in [`interlens.arena.viz.auction_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_page.py#L234-L313)

The adaptation of `page._issue_bars_svg` the tooling map identified as the highest-leverage reuse in the
whole viz stack — same vertical bar, same tick-per-value construction, same single reference rule — with
the issue's option scores replaced by the five seats' valuations and the threshold replaced by the price
the lot actually cleared at. The winner's tick is filled, so "who won it and at what price against what it
was worth to everyone" is one glance per lot.

A lot that went unsold (no bid above reserve) carries no tau-line, which is what an absent clearing price
means and is deliberately not drawn as a price of zero.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `auction` | `dict` | *required* |  |
| `payload` | `dict` | *required* |  |
