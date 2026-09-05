# `ToolCall`

A parsed request from the model to invoke a tool: the tool `name` and its `arguments`.

```python
ToolCall(name: str, arguments: dict = dict(), raw: str = '')
```

Defined in [`interlens.tools.tool_call`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/tools/tool_call.py#L21-L32)

`raw` keeps the exact text the model emitted (useful for debugging a family parser). Tool calls are parsed
out of the generation by a per-family `parse_tool_calls` — the format differs across model families, so the
parsed structure is uniform even though the surface syntax isn't.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `arguments` | `dict` | `dict()` |  |
| `raw` | `str` | `''` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `arguments` | `dict` |  |
| `name` | `str` |  |
| `raw` | `str` |  |
