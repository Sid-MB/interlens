# `reservation_values`

Backward-induction reservation curve `[v_0, v_1, ..., v_T]` where `v_j` is the reservation with `j` rounds remaining; **accept an offer of surplus x iff x >= v_j**.

```python
reservation_values(
	values,
	probs,
	T: int,
	*,
	cost: float = 0.0,
	discount: float = 1.0,
	flow: float = 0.0,
	pmfs=None,
	outside_value: float | None = None,
) -> list
```

Defined in [`interlens.arena.negotiation.acceptance`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/acceptance.py#L55-L94)

v_j = (1 - discount) * flow + discount * E_{X ~ F_{j-1}}[ max(X, v_{j-1}) ] - cost

Parameters
----------
values, probs : sequence[float]
    The stationary offer-surplus distribution `F` as a discrete pmf (support `values`, masses
    `probs`). Ignored if `pmfs` is given.
T : int
    Horizon (max rounds remaining).
cost : float
    Additive per-round search cost `C` (Baarslag friction).
discount : float
    Per-round discount / no-breakdown probability `delta` in `(0, 1]` (McCall friction).
flow : float
    Disagreement flow received while unagreed (enters the discounted continuation).
pmfs : list[tuple[seq, seq]] | None
    Optional per-round distributions `F_{j-1}`; `pmfs[j-1] = (values, probs)` used at step `j` for
    a time-varying offer distribution. Length must be >= `T`.
outside_value : float | None
    Optional floor on every `v_j` (a conservative outside-option reservation utility; Li-Giampapa-
    Sycara). The reservation never drops below it.

Returns `list[float]` of length `T + 1`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `values` |  | *required* |  |
| `probs` |  | *required* |  |
| `T` | `int` | *required* |  |
| `cost` | `float` | `0.0` |  |
| `discount` | `float` | `1.0` |  |
| `flow` | `float` | `0.0` |  |
| `pmfs` |  | `None` |  |
| `outside_value` | `float \| None` | `None` |  |
