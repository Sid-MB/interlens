# `objective_from_normalized`

The table objective of shape `(|D|,)` from a normalized-surplus matrix `z` of shape `(|D|, n)`.

```python
objective_from_normalized(z: np.ndarray) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.fairness`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/fairness.py#L94-L119)

`obj = k/n + geomean_{i in S} z_i / n` with `S` the strictly-satisfied set and `k = |S|` (see the
module docstring for why the two terms compose into MNW's lexicographic rule). A deal satisfying nobody
scores exactly `0`, matching the no-deal payoff. The geometric mean is taken in log space because a
five- or six-party product of small normalized gains underflows well before the mean does.

`z` is **capped at 1** first, and the cap is load-bearing rather than hygiene. The coalition term only
dominates the welfare term if the latter cannot exceed `1/n`, and a party can beat its IR-set ideal on a
deal that leaves somebody else below threshold — uncapped, such a deal can outscore one that satisfies
everybody, which would break both the lexicographic rule and the identity with the Nash Bargaining
Solution. The cap is inert on the IR set (where `z <= 1` by construction), so it costs nothing where the
objective is actually operating; it only refuses to reward paying one party out of another's threshold.

Split out from :func:`mnw_objective` so the private-information path can feed it *expected* normalized
surpluses through :func:`expected_objective` without re-deriving the flattening rule.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z` | `np.ndarray` | *required* |  |
