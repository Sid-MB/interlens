# `context`

Package `interlens.context`

## Modules

- [`context_policy`](context_policy/index.md)
- [`drop_oldest_policy`](drop_oldest_policy/index.md)
- [`error_policy`](error_policy/index.md)
- [`sliding_window_policy`](sliding_window_policy/index.md)
- [`summarize_policy`](summarize_policy/index.md)

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`ContextPolicy`](context_policy/ContextPolicy.md) | `interlens.context.context_policy` | Decides how to fit a participant's view within its model's context window. |
| [`DropOldestPolicy`](drop_oldest_policy/DropOldestPolicy.md) | `interlens.context.drop_oldest_policy` | Drop the oldest `turn` segments (preserving system/moderator/private_context) until the view fits. |
| [`ErrorPolicy`](error_policy/ErrorPolicy.md) | `interlens.context.error_policy` | The safe default: raise if the view exceeds the context window rather than silently dropping content. |
| [`SlidingWindowPolicy`](sliding_window_policy/SlidingWindowPolicy.md) | `interlens.context.sliding_window_policy` | Keep the preserved framing plus the most recent `keep_last` turns; drop older turns. |
| [`SummarizePolicy`](summarize_policy/SummarizePolicy.md) | `interlens.context.summarize_policy` | Compress older turns into a single summary segment instead of dropping them outright (the heaviest policy). |

## Functions

| Name | Summary |
|---|---|
| [`context_policy_from_dict`](context_policy_from_dict.md) |  |
