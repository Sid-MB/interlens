# `conditions`

Module `interlens.stop.conditions`

## Classes

| Name | Summary |
|---|---|
| [`ElapsedTimeStopCondition`](ElapsedTimeStopCondition.md) | Stop once `seconds` of wall-clock have elapsed since the run started (monotonic clock). |
| [`StopStringCondition`](StopStringCondition.md) | Stop when a committed message's visible `content` contains any of the given strings (a done-signal). |
| [`TokenBudget`](TokenBudget.md) | A per-conversation compute budget — the matched-compute primitive for fair solo-vs-pair comparisons. |
| [`TokenStopCondition`](TokenStopCondition.md) | Stop once the total generated tokens across turns reach `max_tokens`. |
| [`TurnStopCondition`](TurnStopCondition.md) | Stop after `max_turns` committed turns. |
