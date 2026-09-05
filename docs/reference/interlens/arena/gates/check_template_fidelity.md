# `check_template_fidelity`

Assert token-id equality between `tokenizer(apply_chat_template(tokenize=False))` and `apply_chat_template(tokenize=True)` for every view.

```python
check_template_fidelity(tokenizer, views: list[list[dict]], **template_kwargs={}) -> dict
```

Defined in [`interlens.arena.gates`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/gates.py#L51-L64)

`template_kwargs` are forwarded to both template
calls (e.g. `enable_thinking=True` for Qwen3, matching the generation-time configuration).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tokenizer` |  | *required* |  |
| `views` | `list[list[dict]]` | *required* |  |
| `template_kwargs` |  | `{}` |  |
