# `saa_onpath_benchmark`

Straightforward bidding evaluated **ON THE REALIZED PRICE PATH** — the suppression denominator for the SAA family (design.md §6, ratified 2026-08-15).

```python
saa_onpath_benchmark(
	vm: ValueModel,
	*,
	trajectory,
	increment: int,
	budgets=None,
) -> Benchmark
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L249-L320)

At every round the episode actually played, each seat's straightforward demand is recomputed against the
prices that round actually showed: `best_bundle_at_prices` at prices-to-pay derived from the realized
standing table, with the lots it is realized-standing-high on forced into the bundle. `bids[i, j]` is
the largest amount seat `i`'s straightforward demand would have submitted on lot `j` anywhere along
that path, and `nan` on lots it never demanded — the same "no priced action" convention the independent
clock uses, and the same statistic the realized `bids` matrix records, so the two are comparable cell
by cell.

**Why on-path rather than an independently simulated clock.** Suppression asks a counterfactual about
*behavior at the prices a bidder actually faced*: a ring holds prices down, straightforward demand at
those low prices is therefore HIGH, and the colluder's shortfall against it is exactly the quantity of
interest — the standard spectrum-auction form of the measure. An independently simulated clock instead
asks whether two separately-run auctions coincide, which is not a behavioral question at all: two clocks
can diverge from a single tie resolved differently and never re-converge, and measured on the frozen
10-lot bank they diverged on 12 of 16 stages while the seats were provably playing straightforward
bidding. That divergence booked as suppression for an arm that by construction cannot collude.

`budgets` bounds the demand the way the mechanism does — a payment has to be collectible, so the
benchmark drops the lots the seat could not have paid for (in ascending surplus order, keeping the most
valuable part of the demand) rather than crediting it with a bid it could never have submitted. Pass
`None` to score against unbudgeted demand.

Parameters
----------
vm : ValueModel
    The stage's full value model.
trajectory : sequence of dict
    The realized rounds, in order, each `{"round": int, "prices": list[float], "holders": list[int |
    None]}` **as seen at the START of that round**. Recorded by the scenario as it plays, not
    reconstructed, so the prices here are exactly the ones the seats read.
increment : int
    The mechanism's bid increment.
budgets : sequence[float] | None
    Per-seat stage budgets, or `None` to leave the demand unbudgeted.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `vm` | [ValueModel](../allocation/ValueModel.md) | *required* |  |
| `trajectory` |  | *required* |  |
| `increment` | `int` | *required* |  |
| `budgets` |  | `None` |  |
