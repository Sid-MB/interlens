# `bid_ladder`

Price against bidding round, every stage of the episode side by side on one shared price scale.

```python
bid_ladder(auction: dict, payload: dict) -> str
```

Defined in [`interlens.arena.viz.auction_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_page.py#L101-L228)

One polyline per seat per stage through the highest price that seat committed in each round — on a clock
format that is the clock price its `stay`/`claim` happened at, since a clock move carries no amount of
its own. Individual lot bids under SAA are drawn as marks rather than folded into the line, because a line
through ten simultaneous lot bids would trace a number nobody bid. A mark that took the standing high is
filled; an irrevocable exit is a cross.

Two overlays make the repeated-play story readable from the one figure: each seat's own top realized
valuation for the stage as a reference tick (post-hoc — no seat saw another's), and a shaded band on any
stage where the outcome rule found an agreement in force, with the onset stage and every defection
labelled on the stage axis.

`None`-safe: a stage with no priced action at all renders as an empty stage column rather than being
dropped, so the stage axis always counts to `T`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `auction` | `dict` | *required* |  |
| `payload` | `dict` | *required* |  |
