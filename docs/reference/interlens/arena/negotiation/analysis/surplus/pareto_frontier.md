# `pareto_frontier`

The non-dominated subset of a set of surplus vectors (the discrete Pareto frontier).

```python
pareto_frontier(surplus_vectors: Sequence[Vec]) -> list[tuple[float, ...]]
```

Defined in [`interlens.arena.negotiation.analysis.surplus`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/surplus.py#L65-L78)

O(|S|^2) brute force, exact at an enumerable deal-space scale. This is a
fallback/utility for fixtures and audits — production frontiers are read from the precomputed
`Instance.solution`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `surplus_vectors` | `Sequence[Vec]` | *required* |  |
