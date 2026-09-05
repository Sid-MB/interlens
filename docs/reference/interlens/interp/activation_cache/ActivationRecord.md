# `ActivationRecord`

One captured tensor plus everything needed to know *what it is*.

```python
ActivationRecord(
	participant: str,
	message_idx: int,
	layer: int,
	site: Site,
	tensor: torch.Tensor,
	token_span: tuple[int, int],
	phases: dict[Phase, tuple[int, int]] = dict(),
)
```

Defined in [`interlens.interp.activation_cache`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/activation_cache.py#L70-L86)

`tensor` is `[seq, d_model]` for one (participant turn, layer, site). `phases` maps `prompt` /
`reasoning` / `answer` to `(start, end)` token indices into that sequence, so reasoning-vs-answer
activations are separable for CoT models. `token_span` is the `(prompt_len, seq_len)` boundary between
the fed-in prompt and the newly generated tokens.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `participant` | `str` | *required* |  |
| `message_idx` | `int` | *required* |  |
| `layer` | `int` | *required* |  |
| `site` | `Site` | *required* |  |
| `tensor` | `torch.Tensor` | *required* |  |
| `token_span` | `tuple[int, int]` | *required* |  |
| `phases` | `dict[Phase, tuple[int, int]]` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `layer` | `int` |  |
| `message_idx` | `int` |  |
| `participant` | `str` |  |
| `phases` | `dict[Phase, tuple[int, int]]` |  |
| `site` | `Site` |  |
| `tensor` | `torch.Tensor` |  |
| `token_span` | `tuple[int, int]` |  |
