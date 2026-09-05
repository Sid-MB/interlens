# `derive_chat_flags`

Probe a tokenizer's chat template to derive `(supports_system_role, requires_alternating_roles)`.

```python
derive_chat_flags(tokenizer) -> tuple[bool, bool]
```

Defined in [`interlens.loading.load`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/loading/load.py#L56-L73)

`supports_system_role` is True iff the template renders a leading `system` turn without raising;
`requires_alternating_roles` is True iff the template rejects two consecutive same-role turns. Each probe is
wrapped in try/except so a raising template simply reads as the corresponding boolean. This replaces per-family
flag declarations: an unknown model gets correct chat behavior with zero configuration.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tokenizer` |  | *required* |  |
