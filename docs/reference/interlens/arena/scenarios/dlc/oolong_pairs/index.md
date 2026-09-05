# `interlens.arena.scenarios.dlc.oolong_pairs`

OOLONG-Pairs: the RLM paper's pairwise-aggregation task (Appendix 12.1).

Data: oolong-synth trec_coarse context windows (Date || User || Instance lines).
Gold: computed programmatically from the dataset's own line labels
(context_window_text_with_labels) — each of the paper's 20 queries is a
predicate over per-user label/date profiles; the answer is the set of
unordered user-ID pairs satisfying it. Score: F1 over the pair set (paper
protocol).

Two conventions the paper leaves implicit (recorded here, applied uniformly
to every arm, so arm comparisons are internally consistent):
  * date conditions ("all instances that are X for both users must be after
    D") are vacuously satisfied by a user with zero X instances;
  * two-sided queries ("one user has A, the other has B") are unordered:
    (u,v) qualifies if u satisfies A and v satisfies B, or vice versa.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `D_APR10` |  |  |
| `D_FEB1` |  |  |
| `D_JAN6` |  |  |
| `D_MAR15` |  |  |
| `D_MAY20` |  |  |
| `LABELS` |  |  |
| `QUERIES` | `list[tuple]` |  |

## Classes

| Name | Summary |
|---|---|
| [`OolongPairsAdapter`](OolongPairsAdapter.md) |  |
| [`Row`](Row.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`gold_pairs`](gold_pairs.md) |  |
| [`parse_lines`](parse_lines.md) | Parse every data line; raises if any 'Date:' line fails to parse. |
| [`question_text`](question_text.md) |  |
