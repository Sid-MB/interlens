# `dominating_alternatives`

Every candidate surplus vector that Pareto-dominates `x`.

```python
dominating_alternatives(x: Vec, candidates: Sequence[Vec]) -> list[Vec]
```

Defined in [`interlens.arena.negotiation.analysis.surplus`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/surplus.py#L58-L62)

Used to flag a *dominated proposal*: a party
proposed/accepted `x` when some other feasible deal made everyone at least as well off and someone
better (a left-on-the-table Pareto improvement).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` | `Vec` | *required* |  |
| `candidates` | `Sequence[Vec]` | *required* |  |
