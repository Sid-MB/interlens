# `truthful_benchmark`

The dominant-strategy benchmark for a ONE-lot second-price (or English) stage: everyone bids its own value [vickrey1961, pp. 20-23].

```python
truthful_benchmark(
	vm: ValueModel,
	*,
	tie_break,
	reserve: int = 0,
	pricing: str = 'second_price',
	bids: np.ndarray | None = None,
	budgets=None,
) -> Benchmark
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L101-L131)

`bids` overrides the truthful bid vector — used by the INTERDEP path, where the benchmark bid is the
conditional expectation rather than the (unknown) realized value.

`budgets` caps each benchmark bid at what the seat can actually pay. Bidding above budget is a LEGALITY
error in this harness (payments must be collectible, design.md §3.2), so `min(value, budget)` — not the
value — is what an information-conditional rational bidder submits. Leaving the cap out scored a
budget-bound seat's legal bid as shading: measured on the `all_rational` arm of the single-lot bank, the
two budget-bound seats of five produced `bid_value_ratio = 0.91` and a spurious `suppression = 0.108`
in a cell where nothing was suppressed. The uncapped own-value vector is kept as `detail["truthful_bids"]`
and reported as the secondary column.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `vm` | [ValueModel](../allocation/ValueModel.md) | *required* |  |
| `tie_break` |  | *required* |  |
| `reserve` | `int` | `0` |  |
| `pricing` | `str` | `'second_price'` |  |
| `bids` | `np.ndarray \| None` | `None` |  |
| `budgets` |  | `None` |  |
