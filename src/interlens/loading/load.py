# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from pathlib import Path

import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, PreTrainedTokenizerBase

from .model_cache import cached_model, cached_tokenizer


def _auto_model_class(hf_id: str, revision: str | None):
	"""Pick the right ``AutoModelFor*`` for ``hf_id`` by peeking at its config.

	Text-only decoders load via ``AutoModelForCausalLM``. Newer-gen releases (Qwen 3.5, Gemma 4, …) ship as
	*multimodal* image-text-to-text wrappers whose config carries a nested ``text_config``; ``AutoModelForCausalLM``
	refuses them, so those load via ``AutoModelForImageTextToText``. The full wrapper is kept (it owns ``generate``
	+ ``lm_head``); text-only generation works with plain ``input_ids`` and ``output_hidden_states`` returns the
	text decoder's states, so the rest of the stack (capture, ``decoder_layers``) is unaffected once
	``decoder_layers`` knows the nested layer path."""
	try:
		cfg = AutoConfig.from_pretrained(hf_id, revision=revision)
	except Exception:
		return AutoModelForCausalLM
	if hasattr(cfg, "text_config"):
		from transformers import AutoModelForImageTextToText
		return AutoModelForImageTextToText
	return AutoModelForCausalLM


def load_tokenizer(hf_id: str, revision: str | None = None) -> PreTrainedTokenizerBase:
	"""Load a tokenizer for ``hf_id`` (or a local path), defaulting ``pad_token`` to ``eos_token`` when absent —
	the single source of the pad-token convention, shared by ``load_model`` and ``AutoModelParticipant`` when it
	has to infer a tokenizer from a bare model."""
	tok = AutoTokenizer.from_pretrained(hf_id, revision=revision)
	if tok.pad_token is None:
		tok.pad_token = tok.eos_token
	return tok


def derive_chat_flags(tokenizer) -> tuple[bool, bool]:
	"""Probe a tokenizer's chat template to derive ``(supports_system_role, requires_alternating_roles)``.

	``supports_system_role`` is True iff the template renders a leading ``system`` turn without raising;
	``requires_alternating_roles`` is True iff the template rejects two consecutive same-role turns. Each probe is
	wrapped in try/except so a raising template simply reads as the corresponding boolean. This replaces per-family
	flag declarations: an unknown model gets correct chat behavior with zero configuration."""

	def _renders(messages) -> bool:
		try:
			tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
			return True
		except Exception:
			return False

	supports_system_role = _renders([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}])
	requires_alternating_roles = not _renders([{"role": "user", "content": "a"}, {"role": "user", "content": "b"}])
	return supports_system_role, requires_alternating_roles


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
	auto_cls = _auto_model_class(hf_id, revision)
	backends = [attn, "sdpa", "eager"]
	last_err = None
	for backend in dict.fromkeys(b for b in backends if b):  # dedupe, keep order
		try:
			model = auto_cls.from_pretrained(hf_id, attn_implementation=backend, **kwargs)
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
	id_or_path: str | Path,
	device: str | torch.device = "cuda",
	dtype: torch.dtype = torch.bfloat16,
	attn: str = "flash_attention_2",
	quant: str | None = None,
	revision: str | None = None,
):
	"""Load a causal LM + tokenizer, sharing through the process-local caches.

	``id_or_path`` is the HF id or a local path to load directly (a ``Path`` is normalized to ``str`` so it shares
	the same cache slot as its string form). Identical (hf_id, device, dtype, attn, quant) pairings share the one
	model object, and the tokenizer is cached by hf_id. Flash-attention is the default with automatic fallback to
	sdpa/eager; quantization is opt-in.
	"""
	hf_id = str(id_or_path)
	tokenizer = cached_tokenizer(hf_id, lambda: load_tokenizer(hf_id, revision=revision))
	weight_key = (hf_id, str(device), str(dtype), attn, quant, revision)
	model = cached_model(weight_key, lambda: _load_model_weights(hf_id, device, dtype, attn, quant, revision))
	return model, tokenizer
