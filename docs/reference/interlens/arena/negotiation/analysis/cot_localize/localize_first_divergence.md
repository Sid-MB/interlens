# `localize_first_divergence`

Binary-search the earliest prefix length `j` (1..n_steps) whose induced action is divergent.

```python
localize_first_divergence(n_steps: int, is_divergent: Callable[[int], bool]) -> int | None
```

Defined in [`interlens.arena.negotiation.analysis.cot_localize`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/cot_localize.py#L47-L66)

`is_divergent(j)` reports whether the action induced by the first `j` steps diverges from the oracle;
it is assumed monotone (non-divergent for short prefixes, divergent once the erroneous step is included),
which is the OmegaPRM prefix-correctness assumption. Returns the first divergent step index (1-based), or
`None` if even the full CoT does not induce a divergent action. Makes O(log n_steps) calls to
`is_divergent` — each call is one (expensive) re-derivation + oracle check in production.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_steps` | `int` | *required* |  |
| `is_divergent` | `Callable[[int], bool]` | *required* |  |
