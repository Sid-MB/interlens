# `interlens.arena.negotiation.space`

The deal space: issues, their discrete options, and the fully-enumerable Cartesian product of options.

A negotiation is over `J` issues, each with a fixed list of discrete options. A **deal** picks one option per
issue and is represented as a `Deal` -- a `tuple[int, ...]` of option indices, one per issue (the frozen
cross-team contract). The whole deal space `D = prod_j |options_j|` is small enough
(|D| ~ 243-3125 in the target regime) to enumerate exactly, which is what makes every normative benchmark in
`solutions.py` exact rather than sampled.

Enumeration order is `itertools.product` order: issue 0 is most significant and the last issue varies
fastest. `deal_at`/`index_of` are the mixed-radix encode/decode for that same order, so a deal's position in
`enumerate()` equals its row in the `|D| x n` utility matrix that `sheets.utility_matrix` builds -- the
NumPy workhorse the solution concepts consume.

Example:

```python
space = DealSpace((Issue("Site", ("North", "South")), Issue("Fund", ("None", "1M", "5M"))))
space.size                       # 6
list(space.enumerate())          # [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)]
space.index_of((1, 2))           # 5
space.deal_at(5)                 # (1, 2)
space.named((1, 2))              # {'Site': 'South', 'Fund': '5M'}
```

## Classes

| Name | Summary |
|---|---|
| [`DealSpace`](DealSpace.md) | The Cartesian product of all issues' options -- the full, enumerable set of possible deals. |
| [`Issue`](Issue.md) | One negotiable issue: a name and its discrete options (order defines the option indices). |
