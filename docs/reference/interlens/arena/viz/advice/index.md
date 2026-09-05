# `interlens.arena.viz.advice`

The advised seat, audited: what its planner knew, what it recommended, and whether the seat did it.

Some arms give one seat a private advisor and let the model keep the decision. Two questions then decide whether
any number the arm produces means anything, and neither is answerable from the transcript:

1. **What did the advisor actually know?** In an interpreter arm the advice is computed from two very different
   evidence channels — the FORMAL move ledger (packages tabled, offers accepted, all machine-readable) and a
   model's parse of the public chat into structured preference claims, each carrying the verbatim quote it was
   read off. A recommendation that looks bizarre usually looks reasonable next to the claims that produced it,
   and a claim that moved a plan is a claim a reader should be able to check against the sentence it came from.
2. **Did the seat take the advice?** An arm whose advice the model discarded measured a prompt, not an
   intervention. On the wave-2 cell 46% of advised turns did something other than what the planner ranked, so a
   reader scrolling the transcript is looking at two quite different kinds of turn and nothing distinguished
   them.

This module renders both, from one run-level sidecar.

The verdict is READ, never computed
-----------------------------------
`advice_trace.json` is written into the run directory by the experiment's own
`build_advice_trace.py`, which takes every compliance column from `advice_uptake` — the module the arm's
uptake gate is evaluated on. Whether a turn followed its advice is therefore decided once, by the code that owns
the comparison rules (deal identity for a propose, offer id for an accept, which rung of a ranked list was
played), and this file only marks what that decision was. Re-deriving it in the renderer would be a second
opinion with no authority, and the two would disagree the first time either changed. It is the same division of
labour as the final-vote tally's derived column (:mod:`~interlens.arena.viz.ballots`).

No model call and no classifier is involved anywhere in the chain. In particular the page does **not** claim to
know how the seat verbalized its advice: it puts the ranked packages, the move actually played, and the public
message the seat published in one place, and leaves the reading to the reader. "Described the advice
faithfully" is not in the record, so it is not asserted.

What ships to the page
----------------------
Each advised turn's trace row is attached to that turn's payload as `advice` and rendered inside its card by
the browser layer (`assets/js_transcript.py`), which also puts an override class on the card and on the
turn's scrubber chip. Above the transcript, :func:`advice_card` renders the same audit as a server-side table,
so the compliance record is readable with scripting off and every row links to its turn.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ADVICE_SIDECAR` |  |  |
| `ROOT_KEY` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`advice_card`](advice_card.md) | The episode's advice audit as one server-rendered section, or `""` when no turn was advised. |
| [`advice_summary`](advice_summary.md) | This episode's compliance record: how many turns were advised, how many followed, on which rung. |
| [`advice_trace`](advice_trace.md) | The optional advice sidecar for a run, or `None` when it is absent or unreadable. |
| [`attach_advice`](attach_advice.md) | Turn payload rows with each advised turn's trace row attached under `advice`. |
| [`episode_advice`](episode_advice.md) | One episode's advised turns from the trace, keyed by turn index as a string. |
| [`round_ledger`](round_ledger.md) | Per round, every advised seat's turn side by side — the shape an all-advised arm is read in. |
| [`round_ledger_card`](round_ledger_card.md) | The per-round, all-seats view, or `""` on an episode that advises fewer than two seats. |
