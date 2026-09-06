# `hazards`

Module `interlens.arena.viz.hazards`

Two facts about a run that decide whether its numbers may be compared with another run's.

Both are properties of the RUN, not of the episode, and both were invisible on the pages for as long as they
existed — which is how each one cost this program weeks.

**Vintage.** A run whose agents carry a since-fixed defect is still a valid record of the agent it actually was,
and is worthless pooled against a repaired run. The convention is a `VINTAGE_PROVENANCE.md` at the run root
naming the defect and its repaired counterpart; :func:`vintage_provenance` reads it and the page turns it into
the loudest thing on the screen.

**Generation budget.** Two arms described as "sharing a protocol" ran at an 8x per-seat token budget difference,
because the frozen caps (2048 on an ordinary turn, 2560 on the forced final) are stamped on every request while
a RAISED cap is stamped only where it was raised. So the default is invisible by design and the exception was
invisible by accident. :func:`generation_budget` reads the caps the turns actually carry — the record, not the
intent — and reports any departure from the frozen pair.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `FROZEN_TURN_CAPS` |  |  |
| `VINTAGE_SCAN_LINES` |  |  |
| `VINTAGE_SUMMARY_CHARS` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`budget_badge`](budget_badge.md) | The per-seat generation budget, stated whenever it is not the frozen default. |
| [`budget_note`](budget_note.md) | A one-line explanation under the header for a non-default generation budget, naming what it blocks. |
| [`generation_budget`](generation_budget.md) | The per-seat generation budget this episode actually ran at, and whether it is the frozen default. |
| [`vintage_badge`](vintage_badge.md) | The sticky quick-read marker for a spoiled vintage, so the hazard survives scrolling past the banner. |
| [`vintage_banner`](vintage_banner.md) | The loudest banner on the page: this run carries a known defect and must not be pooled. |
| [`vintage_pairing`](vintage_pairing.md) | What pairing THESE two episodes means, when either side carries a vintage hazard. |
| [`vintage_provenance`](vintage_provenance.md) | The run's `VINTAGE_PROVENANCE.md`, parsed into `{path, headline, summary}`, or `None` if absent. |
