# `ballot_table`

The final-vote tally as a card, or nothing when the episode has no final-vote phase.

```python
ballot_table(tally: dict | None) -> str
```

Defined in [`interlens.arena.viz.ballots`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/ballots.py#L176-L238)

An abstention is styled as a hazard and stated in words, because the count is the thing that was missing: a
reader who can see "1 of 5 seats cast no ballot" on the page does not need a forensic audit to find the
defect that produced it. The derived column appears only when a sidecar covered at least one turn, and a
recorded-vs-derived disagreement is called a harness bug in the row itself.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tally` | `dict \| None` | *required* |  |
