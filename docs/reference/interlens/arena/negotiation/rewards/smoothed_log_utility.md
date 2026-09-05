# `smoothed_log_utility`

Per-party utility `g(z)` of a normalized surplus: `log z` for `z >= eps`, and below that the tangent line `log(eps) + (z - eps) / eps` (same value and slope at `eps`, so `g` is C1 and strictly increasing on the whole real line).

```python
smoothed_log_utility(
	z: float,
	*,
	eps: float = DEFAULT_EPS,
	g_floor: float | None = None,
) -> float
```

Defined in [`interlens.arena.negotiation.rewards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/rewards.py#L60-L89)

Unbounded below by default, which was the original intent: deep threshold violations
are meant to hurt.

`g_floor` clips that unbounded tail from below at a constant, `max(g(z), g_floor)`. Leave it `None` for
the original unbounded shape. Pass a value when the *dynamic range* of the violation branch is the problem
rather than its direction: because the linear branch is unbounded, one party at `z = -0.2` contributes
`-25.6` against a well-behaved deal's `-2`ish, so nearly all variance in `table_reward` — and therefore
nearly all gradient — lives in "did anybody get shorted" rather than in "was the surplus divided well". A
floor bounds the violation term's contribution and lets the among-IR region carry the signal, at the cost of
making `g` non-strict (flat) below the crossing point `z*` where `g(z*) = g_floor`.

**The floor must sit strictly below** :func:`no_deal_utility` (`-5.605` at the default `eps`) or the
ordering inverts and a below-threshold agreement becomes worth more than walking away, which is the one
ordering the linear branch exists to protect. This is checked, not documented-and-hoped.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z` | `float` | *required* |  |
| `eps` | `float` | `DEFAULT_EPS` |  |
| `g_floor` | `float \| None` | `None` |  |
