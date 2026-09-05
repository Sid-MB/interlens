# `MessageHook`

Middleware that inspects each freshly generated message *before* it is committed to the transcript, and may approve / deny / edit it.

```python
MessageHook()
```

Defined in [`interlens.hooks.message_hook`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/hooks/message_hook.py#L52-L64)

**Inherits from:** `ABC`

This is the seam for a future LLM-judge that vets or rewrites turns (e.g. safety filtering, format
enforcement). Hooks live on the live `Conversation` (`conversation.message_hooks`) and are NOT serialized
in the template — they're a runtime policy, not part of the scenario recipe. The default is an empty hook
list, i.e. today's pass-through behavior.

## Methods {#methods}

## `review` {#review}

```python
review(self, message: 'Message', conversation: 'Conversation') -> MessageHookResult
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/hooks/message_hook.py#L62-L64)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `'Message'` | *required* |  |
| `conversation` | `'Conversation'` | *required* |  |
