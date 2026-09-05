# `ToolResult`

The outcome of executing a `ToolCall`: the tool `name` and its string `output` (or error text).

```python
ToolResult(name: str, output: str, error: bool = False)
```

Defined in [`interlens.tools.tool_call`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/tools/tool_call.py#L35-L41)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `output` | `str` | *required* |  |
| `error` | `bool` | `False` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `error` | `bool` |  |
| `name` | `str` |  |
| `output` | `str` |  |
