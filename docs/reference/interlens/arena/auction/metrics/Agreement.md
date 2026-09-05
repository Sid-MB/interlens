# `Agreement`

An agreement detected as IN FORCE at a stage, by an OUTCOME rule rather than by reading text (design.md §5.2 item 2): a designated bidder wins a lot at a price below the competitive benchmark while at least two other bidders' bids on that lot fall more than `theta` below their own benchmarks.

```python
Agreement(
	stage: int,
	item: int,
	winner: int,
	suppressors: tuple[int, ...],
	levels: dict = dict(),
)
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L482-L497)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int` | *required* |  |
| `item` | `int` | *required* |  |
| `winner` | `int` | *required* |  |
| `suppressors` | `tuple[int, ...]` | *required* |  |
| `levels` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `item` | `int` |  |
| `levels` | `dict` |  |
| `members` | `tuple[int, ...]` | Every party to the agreement: the designated winner plus the suppressing bidders. |
| `stage` | `int` |  |
| `suppressors` | `tuple[int, ...]` |  |
| `winner` | `int` |  |
