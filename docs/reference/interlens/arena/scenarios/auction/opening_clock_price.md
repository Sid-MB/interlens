# `opening_clock_price`

Where a clock family's price starts in each stage.

```python
opening_clock_price(spec) -> int
```

Defined in [`interlens.arena.scenarios.auction`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction.py#L104-L115)

The two clocks run in opposite directions and start at opposite ends: a DESCENDING (Dutch) clock starts
above every realized valuation and falls, while an ASCENDING (English) clock starts at the RESERVE and
rises. Deriving both from :func:`clock_start` without the direction was a real bug — it opened the English
clock above every value, so every seat exited in the first round and the stage ended before any price
discovery happened at all.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `spec` |  | *required* |  |
