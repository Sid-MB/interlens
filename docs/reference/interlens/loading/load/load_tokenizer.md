# `load_tokenizer`

Load a tokenizer for `hf_id` (or a local path), defaulting `pad_token` to `eos_token` when absent — the single source of the pad-token convention, shared by `load_model` and `AutoModelParticipant` when it has to infer a tokenizer from a bare model.

```python
load_tokenizer(hf_id: str, revision: str | None = None) -> PreTrainedTokenizerBase
```

Defined in [`interlens.loading.load`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/loading/load.py#L46-L53)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `hf_id` | `str` | *required* |  |
| `revision` | `str \| None` | `None` |  |
