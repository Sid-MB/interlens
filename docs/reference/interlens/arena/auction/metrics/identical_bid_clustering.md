# `identical_bid_clustering`

The WEAK-cartel signature: bidders submitting the SAME bid rather than transferring money.

```python
identical_bid_clustering(out: StageOutcome, members=None) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L319-L346)

McAfee-McMillan's weak cartel cannot make side payments, so the best it can do is have members submit
identical bids, sacrificing efficiency to suppress price. The design names that prediction and defines no
statistic for it; this is the statistic. Per lot, the largest set of seats whose bids are exactly equal,
over the seats in `members` (all of them when `members` is `None`).

Returns `{"max_cluster", "clustered", "n"}` — the largest equal-bid group on any lot, whether it reached
two, and the number of (seat, lot) bids the statistic saw. `n = 0` with `max_cluster` `nan` where no
seat took a priced action, which is a real state on a clock and must not read as "no clustering found".

Whole-number bids over a small range make some coincidental equality certain, so this number is meaningless
without its no-coordination floor: the free arms bid deterministic best responses to distinct draws, so
THEIR rate on the same bank is the floor, and the program's rule is to compute it before believing any
number this returns.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out` | [StageOutcome](StageOutcome.md) | *required* |  |
| `members` |  | `None` |  |
