# `MessageHookResult`

```python
MessageHookResult(action: HookAction, message: 'Message | None' = None)
```

Defined in [`interlens.hooks.message_hook`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/hooks/message_hook.py#L34-L49)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | [HookAction](HookAction.md) | *required* |  |
| `message` | `'Message | None'` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `action` | [HookAction](HookAction.md) |  |
| `message` | `'Message | None'` |  |

## Methods {#methods}

## `approve` {#approve}

```python
approve(cls) -> 'MessageHookResult'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/hooks/message_hook.py#L39-L41)

## `deny` {#deny}

```python
deny(cls) -> 'MessageHookResult'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/hooks/message_hook.py#L43-L45)

## `edit` {#edit}

```python
edit(cls, message) -> 'MessageHookResult'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/hooks/message_hook.py#L47-L49)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` |  | *required* |  |
