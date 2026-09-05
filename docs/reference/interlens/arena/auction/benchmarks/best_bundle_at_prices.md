# `best_bundle_at_prices`

The bundle maximizing `V_i(S) - sum_{j in S} price_j` subject to capacity, by exact enumeration over bundles of size at most `k_i` — straightforward bidding's demand correspondence [milgrom2000].

```python
best_bundle_at_prices(
	vm: ValueModel,
	seat: int,
	prices: np.ndarray,
	forced: tuple[int, ...] = (),
) -> tuple[tuple[int, ...], float]
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L221-L246)

`forced` items are held (the lots the seat is already standing high on, which it cannot walk away from
within the stage). Ties break toward the SMALLER bundle and then the lexicographically first, so the
simulation is deterministic.

A seat's DEMAND is what makes this the information-conditional benchmark: a capacity-`k` bidder facing 20
lots demands at most `k` of them, so the lots outside its demand are lots a rational bidder places no
priced action on -- not lots it suppressed.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `vm` | [ValueModel](../allocation/ValueModel.md) | *required* |  |
| `seat` | `int` | *required* |  |
| `prices` | `np.ndarray` | *required* |  |
| `forced` | `tuple[int, ...]` | `()` |  |
