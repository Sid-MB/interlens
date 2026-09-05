# `interlens.tools`

## Modules

- [`registry`](registry/index.md)
- [`tool`](tool/index.md)
- [`tool_call`](tool_call/index.md)

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`DEFAULT_REGISTRY`](registry/index.md#attributes) | `interlens.tools.registry` |  |
| [`Tool`](tool/Tool.md) | `interlens.tools.tool` | A capability a participant can invoke during its turn. |
| [`ToolCall`](tool_call/ToolCall.md) | `interlens.tools.tool_call` | A parsed request from the model to invoke a tool: the tool `name` and its `arguments`. |
| [`ToolRegistry`](registry/ToolRegistry.md) | `interlens.tools.registry` | Resolves tool *names* (which serialize) to live `Tool` instances (which don't). |
| [`ToolResult`](tool_call/ToolResult.md) | `interlens.tools.tool_call` | The outcome of executing a `ToolCall`: the tool `name` and its string `output` (or error text). |
