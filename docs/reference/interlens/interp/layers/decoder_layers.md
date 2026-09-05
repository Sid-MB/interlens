# `decoder_layers`

Return the list of transformer decoder layer modules, across common HF architectures.

```python
decoder_layers(model: 'PreTrainedModel')
```

Defined in [`interlens.interp.layers`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/layers.py#L24-L48)

Steering/patching hooks and per-layer capture all need the ordered layer stack. Qwen and Gemma both expose
it at `model.model.layers`; a few fallbacks cover other families so the interp layer isn't Qwen/Gemma-only.
Multimodal image-text-to-text wrappers (Qwen 3.5, Gemma 4, …) nest the text decoder one level deeper — its
layers live at `model.language_model.layers` (or `.model.language_model.model.layers`) — so those paths are
included too. PEFT/adapter wrappers (`PeftModelForCausalLM`) are unwrapped first so hooks land on the real
decoder layers.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |
