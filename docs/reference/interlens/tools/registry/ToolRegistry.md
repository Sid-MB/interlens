# `ToolRegistry`

Resolves tool *names* (which serialize) to live `Tool` instances (which don't).

```python
ToolRegistry()
```

Defined in [`interlens.tools.registry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/tools/registry.py#L21-L43)

This is the tools analogue of the model registry: a template stores `tool_names` and, at `build` time on
each worker, the registry turns them into callables. Because spawned worker processes inherit no parent
state, tools must be registered at import time (or via a worker-init hook), not imperatively in the parent.

## Methods {#methods}

## `register` {#register}

```python
register(self, tool: Tool) -> Tool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/tools/registry.py#L32-L34)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tool` | [Tool](../tool/Tool.md) | *required* |  |

## `resolve` {#resolve}

```python
resolve(self, names) -> list[Tool]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/tools/registry.py#L36-L40)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `names` |  | *required* |  |
