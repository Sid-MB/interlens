# `final_ballots`

The episode's final vote as `{offer, rows, n_ballots, n_abstentions, n_retries, n_mismatch, derived}`.

```python
final_ballots(payload: dict, derivation: dict | None = None) -> dict
```

Defined in [`interlens.arena.viz.ballots`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/ballots.py#L106-L173)

`rows` is one entry per PUBLISHED final-vote turn in order, carrying the seat, the kind of occupant, the
recorded ballot, the parser's complaint when there was one, and — when the sidecar covers the turn — what the
seat's own policy re-derives and whether the record matches it. `offer` is the package under the vote,
taken from the offer id the forced final proposal was registered under and falling back to whichever id the
ballots themselves reference, so a protocol whose final proposal is not in the ledger still names its own
question.

Returns `{"rows": []}` for an episode with no final-vote phase, which is most protocols; the page renders
nothing rather than an empty table.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
| `derivation` | `dict \| None` | `None` |  |
