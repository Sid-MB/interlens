from __future__ import annotations

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedTokenizerBase

from .registry import resolve, tokenizer_id
from .model_cache import cached_model, cached_tokenizer


def load_tokenizer(hf_id: str, revision: str | None = None) -> PreTrainedTokenizerBase:
	"""Load a tokenizer for ``hf_id`` (or a local path), defaulting ``pad_token`` to ``eos_token`` when absent —
	the single source of the pad-token convention, shared by ``load_model`` and ``AutoModelParticipant`` when it
	has to infer a tokenizer from a bare model."""
	tok = AutoTokenizer.from_pretrained(hf_id, revision=revision)
	if tok.pad_token is None:
		tok.pad_token = tok.eos_token
	return tok


def _load_model_weights(hf_id, device, dtype, attn, quant, revision):
	"""Load weights, trying flash-attn first and gracefully falling back. Records nothing here; the caller/
	participant records the *resolved* backend in config metadata."""
	kwargs = dict(dtype=dtype, revision=revision)
	if quant is not None:
		# Quantization is opt-in (perturbs activations/logits → interp fidelity). cuda-only in practice.
		from transformers import BitsAndBytesConfig
		if quant == "4bit":
			kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)
		elif quant == "8bit":
			kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)

	# Try the requested attention backend, then progressively simpler ones, so flash-attn-by-default never
	# hard-fails on hardware/builds that lack it.
	backends = [attn, "sdpa", "eager"]
	last_err = None
	for backend in dict.fromkeys(b for b in backends if b):  # dedupe, keep order
		try:
			model = AutoModelForCausalLM.from_pretrained(hf_id, attn_implementation=backend, **kwargs)
			model.eval()
			model._resolved_attn = backend  # traceable in saved metadata
			if quant is None:
				model = model.to(device)
			return model
		except Exception as exc:  # unsupported backend / missing package → fall back
			last_err = exc
			continue
	raise RuntimeError(f"failed to load {hf_id} under any attention backend: {last_err}")


def load_model(
	id_or_name: str,
	device: str | torch.device = "cuda",
	dtype: torch.dtype = torch.bfloat16,
	attn: str = "flash_attention_2",
	quant: str | None = None,
	revision: str | None = None,
):
	"""Load a causal LM + tokenizer, sharing through the process-local caches.

	Results: same-family/different-size pairings share the tokenizer (via ``tokenizer_id``); identical
	(hf_id, device, dtype, attn, quant) pairings share the one model object. Flash-attention is the default
	with automatic fallback to sdpa/eager; quantization is opt-in.
	"""
	hf_id, _ = resolve(id_or_name)
	tok_id = tokenizer_id(id_or_name)
	tokenizer = cached_tokenizer(tok_id, lambda: load_tokenizer(hf_id, revision=revision))
	weight_key = (hf_id, str(device), str(dtype), attn, quant, revision)
	model = cached_model(weight_key, lambda: _load_model_weights(hf_id, device, dtype, attn, quant, revision))
	return model, tokenizer
