# `saa_competitive_benchmark`

Simulate an INDEPENDENT simultaneous ascending auction under straightforward bidding [milgrom2000, pp. 250-258] — a **descriptive** revenue and efficiency ceiling, never a suppression denominator.

```python
saa_competitive_benchmark(
	vm: ValueModel,
	*,
	increment: int,
	reserve: int = 0,
	tie_break,
	round_cap: int = 200,
) -> Benchmark
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L323-L400)

Ratified 2026-08-15 (design.md §6): this form is reported beside the on-path measure as
`benchmark_independent_clock` and is path-INDEPENDENT by construction — it starts from the reserve and
runs its own clock, so it answers "what would a clean straightforward-bidding auction on these draws have
raised and achieved", not "did this bidder suppress". It must not be used as a per-lot bid benchmark:
every contested round is an exact tie (all raisers bid `standing + increment`), and one tie resolved
differently sends the two clocks down permanently different paths, so its per-lot bids diverge from any
realized run's for reasons that are not behavioral. Use :func:`saa_onpath_benchmark` for suppression.

Every round, each seat computes its surplus-maximizing bundle at "prices to pay" (the standing price on
lots it already holds, standing + `increment` on lots it does not) and bids `standing + increment` on
any lot in that bundle it does not hold. The clock stops when a round passes with no new bid, or at
`round_cap`. The resulting standing prices are the competitive benchmark prices, and the resulting
assignment is the competitive benchmark allocation.

**The per-lot benchmark BID is information-conditional** (design.md v2.1 implementation notes, ratified
2026-08-15): the seat's own value `v_ij` on the lots it ever DEMANDED in the simulation, and `nan` on
the lots it never demanded. Under APV that is the change that makes suppression mean what the metric says
it means. A capacity-2 bidder facing 20 lots rationally places no priced action on 18 of them; scoring
those 18 cells against its own value -- which the previous all-lots truthful matrix did -- booked a
capacity constraint as suppression and made `all_rational` read as a colluding arm. The full own-value
matrix survives as `detail["truthful_bids"]` and is reported as the secondary suppression column, so both
numbers are always visible.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `vm` | [ValueModel](../allocation/ValueModel.md) | *required* |  |
| `increment` | `int` | *required* |  |
| `reserve` | `int` | `0` |  |
| `tie_break` |  | *required* |  |
| `round_cap` | `int` | `200` |  |
