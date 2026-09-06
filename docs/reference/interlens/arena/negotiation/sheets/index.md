# `sheets`

Module `interlens.arena.negotiation.sheets`

Private score sheets, the additive utility model, the game specification, and the NumPy utility matrix.

Each party holds a secret **score sheet**: an integer/real value for every option of every issue, plus a
private acceptance **threshold** `tau_i` (its BATNA / reservation value). Utility is the Keeney-Raiffa additive
form `u_i(d) = sum_j s_ij(d_j)` [keeney_raiffa1976]; the analysis object is always the **surplus**
`x_i(d) = u_i(d) - tau_i` -- raw points sit on arbitrary private scales, so only scale-invariant solution
concepts (Nash product, Kalai-Smorodinsky) are defensible across parties (see `solutions.py`).

`GameSpec` bundles the deal space, the sheets, and the protocol knobs (rounds, full/private info, chat on/off,
proposer/veto seats, agreement rule) into one object that round-trips through a plain JSON dict, so a whole game
drops straight into an arena `Instance.payload` and back.

The **workhorse** every solution concept consumes is :func:`utility_matrix` -- the dense `|D| x n` array
`U[k, i] = u_i(deal_at(k))` built once via a vectorized mixed-radix accumulation (no Python loop over deals).

Example:

```python
space = DealSpace((Issue("A", ("a0", "a1")), Issue("B", ("b0", "b1", "b2"))))
alice = ScoreSheet("Alice", ((10, 0), (0, 3, 6)), threshold=5.0)
alice.utility((1, 2))            # 0 + 6 = 6.0
alice.surplus((1, 2))            # 6 - 5 = 1.0
U = utility_matrix(space, (alice, bob))     # shape (6, 2)
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `CONSTRAINTS` | `dict[str, 'Callable[[Deal], bool]']` |  |

## Classes

| Name | Summary |
|---|---|
| [`GameSpec`](GameSpec.md) | A complete negotiation game: the deal space, every party's private sheet, and the protocol knobs. |
| [`ScoreSheet`](ScoreSheet.md) | One party's private additive score sheet. |

## Functions

| Name | Summary |
|---|---|
| [`pairwise_iou`](pairwise_iou.md) | Mean pairwise Intersection-over-Union of the parties' *value supports* -- the score-function-overlap descriptor of the TMLR reproduction [reproB_tmlr] (their games run 18.8-29.8%). |
| [`register_constraint`](register_constraint.md) | Register a structural deal predicate under `name` for `GameSpec(constraint=name)`. |
| [`sparsity`](sparsity.md) | Fraction of option cells (over all sheets, issues, options) whose value is exactly zero -- the score-sheet sparsity descriptor of the TMLR reproduction [reproB_tmlr] (their games run 23.7-43.0%). |
| [`surplus_matrix`](surplus_matrix.md) | The `\|D\| x n` surplus matrix `U - tau`. |
| [`utility_matrix`](utility_matrix.md) | Build the dense `\|D\| x n` utility matrix `U[k, i] = u_i(space.deal_at(k))`. |
