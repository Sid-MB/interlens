# `ballots`

Module `interlens.arena.viz.ballots`

The final vote, as a tally a reader can check at a glance — including the ballots that were never recorded.

The forced final is the one turn where every seat must answer the same question about the same package, so it is
the one place in an episode where a missing answer is unambiguous. It is also where a defect hid for weeks: a
computable seat cast its up/down vote on whichever live offer it valued most rather than on the offer actually
under the vote, the protocol rejected that as illegal, the seat repeated itself on its single retry, and the turn
was recorded as a **pass**. A pass parses cleanly, so the episode closed, the status said `done`, and 99% of
one arm's final ballots were silent abstentions that nothing on the page mentioned.

So the tally is deliberately built around absence. Every seat that should have voted gets a row whether or not it
produced a ballot, and a seat with no recorded ballot is called an abstention in the loudest style the page has.

**And "abstention" is where the page stops describing and starts quoting**, because the word undersells what
happened. The seat did not decline to vote: it voted, on the wrong offer id, and the record kept nothing. Both
halves of that signature are in the record — the protocol's rejection (`"The final vote is only on P9; reference
that offer id."`) and the seat's own response (`{"action": "accept", "offer_id": "P6"}`) — so the row prints
both verbatim rather than paraphrasing either. Everything downstream that called this a silent abstention was
describing the record's shape instead of the agent's behaviour.

**Derived ballots.** Where a computable policy occupied the seat, its vote has an offline answer, and gate G3
(`experiments/rational_agents/gate_seeded_offer_votes.py`) already re-derives exactly that by replaying the
policy against the view the seat really saw. Re-implementing it in the renderer would be a second opinion with
no authority, so this reads the gate's own output instead, from an optional `vote_derivation.json` at the run
root with the shape:

```python
{"episodes": {"<episode_id>": {"<turn_idx>": {"expected": {...}, "recorded": {...}, "match": false}}}}
```

Absent sidecar, absent run, or an episode the gate did not cover: the derived column is omitted and the recorded
tally stands on its own, which is already the part that makes the defect visible.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ATTEMPT_EXCERPT_CHARS` |  |  |
| `BALLOT_ACTIONS` |  |  |
| `DERIVATION_SIDECAR` |  |  |
| `FINAL_PROPOSAL_PHASE` |  |  |
| `FINAL_VOTE_PHASE` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`ballot_table`](ballot_table.md) | The final-vote tally as a card, or nothing when the episode has no final-vote phase. |
| [`final_ballots`](final_ballots.md) | The episode's final vote as `{offer, rows, n_ballots, n_abstentions, n_retries, n_mismatch, derived}`. |
| [`vote_derivation`](vote_derivation.md) | The optional per-turn re-derivation sidecar for a run, or `None` when it is absent or unreadable. |
