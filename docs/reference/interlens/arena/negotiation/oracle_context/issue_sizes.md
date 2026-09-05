# `issue_sizes`

Per-issue option counts `(O_1, ..., O_J)`, discovered from (in order): an `.issue_sizes` / `.n_options` attribute on the space; a sheet's `.values` rows; or the max option index seen in `deals`.

```python
issue_sizes(
	space: DealSpace | None = None,
	sheets: Iterable[ScoreSheet] | None = None,
	deals: list[Deal] | None = None,
) -> tuple[int, ...]
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L70-L89)

Needed by the belief oracle to build per-issue evaluator hypotheses.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `space` | [DealSpace](../space/DealSpace.md) \| None | `None` |  |
| `sheets` | Iterable[[ScoreSheet](../sheets/ScoreSheet.md)] \| None | `None` |  |
| `deals` | `list[Deal] \| None` | `None` |  |
