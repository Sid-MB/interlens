# `stop`

Package `interlens.stop`

## Modules

- [`conditions`](conditions/index.md)
- [`stop_condition`](stop_condition/index.md)

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`AnyStopCondition`](stop_condition/AnyStopCondition.md) | `interlens.stop.stop_condition` | Fires when *any* member condition fires. |
| [`ElapsedTimeStopCondition`](conditions/ElapsedTimeStopCondition.md) | `interlens.stop.conditions` | Stop once `seconds` of wall-clock have elapsed since the run started (monotonic clock). |
| [`StopCondition`](stop_condition/StopCondition.md) | `interlens.stop.stop_condition` | A stateful predicate that ends a `Conversation.run` early. |
| [`StopStringCondition`](conditions/StopStringCondition.md) | `interlens.stop.conditions` | Stop when a committed message's visible `content` contains any of the given strings (a done-signal). |
| [`TokenBudget`](conditions/TokenBudget.md) | `interlens.stop.conditions` | A per-conversation compute budget — the matched-compute primitive for fair solo-vs-pair comparisons. |
| [`TokenStopCondition`](conditions/TokenStopCondition.md) | `interlens.stop.conditions` | Stop once the total generated tokens across turns reach `max_tokens`. |
| [`TurnStopCondition`](conditions/TurnStopCondition.md) | `interlens.stop.conditions` | Stop after `max_turns` committed turns. |
| [`active_stop_conditions`](stop_condition/active_stop_conditions.md) | `interlens.stop.stop_condition` | The stop conditions currently installed by enclosing `with condition:` blocks (outermost first). |
