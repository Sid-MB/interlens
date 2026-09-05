# `value_to_go_full_info_cached`

:func:`value_to_go_full_info` memoized on the game tables — the whole `V` curve, computed ONCE.

```python
value_to_go_full_info_cached(
	tables: GameTables,
	proposer_seq,
	T: int,
	discount: float = 0.95,
	*,
	min_accept: int | None = None,
	veto_seats=(),
) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.bestresponse`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/bestresponse.py#L281-L310)

The joint value curve depends only on `(tables, proposer_seq, T, discount, min_accept, veto_seats)`,
every one of which is fixed for an episode; a turn varies only which ROW of `V` it reads. Recomputing
the full backward induction on every turn therefore costs `O(T)` Poisson-binomial solves per turn and
`O(T^2)` per episode, which is what made a long-horizon omniscient seat expensive the moment it started
planning the real deadline. The cache lives on the `GameTables` instance (one per game, already cached
on the game itself), so it is per-game rather than global and needs no eviction policy; the stored array
is marked read-only so a caller cannot mutate a shared curve. Falls back to a plain recompute if the
tables object refuses the attribute.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
| `proposer_seq` |  | *required* |  |
| `T` | `int` | *required* |  |
| `discount` | `float` | `0.95` |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` |  | `()` |  |
