# `interlens.arena.scenarios.dlc`

Task adapters for the distributed long-context scenario, ported from the RLM paper's benchmarks.

Each adapter defines one task's question format, answer parsing, and exact grading for
`DistributedLongContext`; `interlens.arena.scenarios.dlc.build` builds the corresponding instance banks
from the benchmarks' own sources (pinned revisions; no benchmark data ships in this repo).

- `SniahAdapter` — RULER-style single needle-in-a-haystack (exact match on the magic number).
- `OolongPairsAdapter` — OOLONG-Pairs pairwise aggregation (F1 over the emitted pair set; the task whose
  full enumeration models decline — see the `capitulated` outcome class).
- `CodeQAAdapter` — LongBench-v2 repo-understanding multiple choice (exact choice match).
- `BCPAdapter` — BrowseComp-Plus multi-hop QA. Grading is two-phase: the scenario records the submitted
  answer un-judged (`primary=0`, `judged=False`); apply the official grader template
  (`bcp.GRADER_TEMPLATE`, pinned verbatim from the benchmark repo) with an LLM judge post-hoc.

## Modules

- [`bcp`](bcp/index.md) — BrowseComp-Plus: multi-hop QA over a fixed document corpus (paper §3.1).
- [`build`](build/index.md) — Instance builders for the distributed long-context tasks — fetch, shard, and save instance banks.
- [`codeqa`](codeqa/index.md) — LongBench-v2 CodeQA: repo-understanding multiple choice (paper §3.1).
- [`oolong_pairs`](oolong_pairs/index.md) — OOLONG-Pairs: the RLM paper's pairwise-aggregation task (Appendix 12.1).
- [`sniah`](sniah/index.md) — S-NIAH: RULER-style single needle-in-a-haystack (paper §3.1).

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`BCPAdapter`](bcp/BCPAdapter.md) | `interlens.arena.scenarios.dlc.bcp` |  |
| [`CodeQAAdapter`](codeqa/CodeQAAdapter.md) | `interlens.arena.scenarios.dlc.codeqa` |  |
| [`GRADER_TEMPLATE`](bcp/index.md#attributes) | `interlens.arena.scenarios.dlc.bcp` |  |
| [`OolongPairsAdapter`](oolong_pairs/OolongPairsAdapter.md) | `interlens.arena.scenarios.dlc.oolong_pairs` |  |
| [`SniahAdapter`](sniah/SniahAdapter.md) | `interlens.arena.scenarios.dlc.sniah` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ADAPTERS` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`dlc_scenario`](dlc_scenario.md) | A `DistributedLongContext` scenario for one task, e.g. `dlc_scenario("sniah")`. |
