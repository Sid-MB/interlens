# `interlens.arena.scenarios.dlc.codeqa`

LongBench-v2 CodeQA: repo-understanding multiple choice (paper §3.1).

Context: a concatenated code repository (LongBench-v2 'Code Repository
Understanding'); question + 4 choices; grading = exact choice match
(official LongBench-v2 protocol).

Sharding note: LongBench contexts carry no reliable file markers (verified
2026-07-20), so shards are contiguous line-block splits balanced by
characters — approximating "each agent owns part of the codebase".

## Classes

| Name | Summary |
|---|---|
| [`CodeQAAdapter`](CodeQAAdapter.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`question_text`](question_text.md) |  |
