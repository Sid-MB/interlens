# `value_to_go_full_info`

Joint continuation values `V[t]` (shape `(T+2, n)`) for *every* seat under subgame-perfect alternating-offers play with the fixed `min_accept` quorum, required `veto_seats`, and no-deal surplus 0.

```python
value_to_go_full_info(
	tables: GameTables,
	proposer_seq,
	T: int,
	discount: float = 0.95,
	*,
	min_accept: int | None = None,
	veto_seats=(),
) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.bestresponse`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/bestresponse.py#L252-L278)

`min_accept=None` preserves unanimity.

`V[t, i]` = seat `i`'s expected surplus-to-go at the start of round `t` (t = 1..T; `V[T+1] = 0`).
At round `t` the proposer `p = proposer_seq[(t-1) % len]` offers the all-accepted deal maximizing its
own surplus if that beats delaying, else delays; responders accept iff their surplus >= their discounted
continuation.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
| `proposer_seq` |  | *required* |  |
| `T` | `int` | *required* |  |
| `discount` | `float` | `0.95` |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` |  | `()` |  |
