# `load`

Module `interlens.loading.load`

## Functions

| Name | Summary |
|---|---|
| [`derive_chat_flags`](derive_chat_flags.md) | Probe a tokenizer's chat template to derive `(supports_system_role, requires_alternating_roles)`. |
| [`load_model`](load_model.md) | Load a causal LM + tokenizer, sharing through the process-local caches. |
| [`load_tokenizer`](load_tokenizer.md) | Load a tokenizer for `hf_id` (or a local path), defaulting `pad_token` to `eos_token` when absent — the single source of the pad-token convention, shared by `load_model` and `AutoModelParticipant` when it has to infer a tokenizer from a bare model. |
