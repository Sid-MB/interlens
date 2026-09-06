# `bcp`

Module `interlens.arena.scenarios.dlc.bcp`

BrowseComp-Plus: multi-hop QA over a fixed document corpus (paper §3.1).

Corpus per instance: gold + evidence docs guaranteed present + seeded filler
negatives up to k docs (paper: k=1000; our k set by the stage-4 feasibility
gate). Queries/answers decrypted with the dataset's published canary.

Grading is TWO-PHASE: the env records the submitted answer with
primary=0/judged=False; `judge_bcp.py` then applies the official BrowseComp
GRADER_TEMPLATE (pinned verbatim from github.com/texttron/BrowseComp-Plus,
search_agent/prompts.py) via a Claude judge and rewrites episode outcomes.
Judge model substitution (paper used OpenAI judges) is recorded per episode.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `GRADER_TEMPLATE` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`BCPAdapter`](BCPAdapter.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`question_text`](question_text.md) |  |
