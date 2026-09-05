# `GenerationFailureBudgetExceeded`

Raised by :class:`BatchedEpisodePool` when it has had to fabricate more turns than its budget allows.

```python
GenerationFailureBudgetExceeded()
```

Defined in [`interlens.arena.engine`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L120-L126)

**Inherits from:** `RuntimeError`

The alternative — which this replaces — is a run that completes, reports `status="done"` and
`parse_ok=True` on every turn, and contains no model behaviour whatsoever. A campaign cell has been
observed at 100% fabricated turns while reporting clean. Failing loudly in the first seconds is strictly
better than discovering it in the analysis, so the budget defaults to ON.
