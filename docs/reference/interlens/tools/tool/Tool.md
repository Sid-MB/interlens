# `Tool`

A capability a participant can invoke during its turn.

```python
Tool()
```

Defined in [`interlens.tools.tool`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/tools/tool.py#L21-L43)

**Inherits from:** `ABC`

A tool has a `name`, a JSON `schema` (in the function-calling format chat templates render via their
`tools=` argument), and is callable with keyword arguments to produce a string result. Tools contain live
callables and so are NOT serializable — templates store tool *names* and resolve them against a
`ToolRegistry` at build time, mirroring how models are resolved from ids.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` | `str` |  |
| `schema` | `dict` | The tool's JSON function schema, e.g. `{"type": "function", "function": {"name", "description", "parameters": {...}}}`, passed straight to `apply_chat_template(tools=...)` so each family renders it in its native format. |
