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

from .devices import device_map_kind
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


def _load_model_weights(hf_id, device, dtype, attn, quant, revision, max_memory=None):
	"""Load weights, trying flash-attn first and gracefully falling back. Records nothing here; the caller/
	participant records the *resolved* backend in config metadata.

	``device`` is either an ordinary placement (``"cuda"``, ``"cuda:1"``, a ``torch.device``) — loaded then
	``.to()``'d, the historical path — or a sharding strategy (``"auto"`` and friends, or an explicit map), in
	which case it is passed straight through as ``device_map=`` and the ``.to()`` is skipped, because moving a
	sharded model would undo the placement accelerate just computed."""
	device_map = device_map_kind(device)
	kwargs = dict(dtype=dtype, revision=revision)
	if device_map is not None:
		kwargs["device_map"] = device_map
	if max_memory is not None:
		kwargs["max_memory"] = dict(max_memory)
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
			if quant is None and device_map is None:
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
	max_memory: dict | None = None,
):
	"""Load a causal LM + tokenizer, sharing through the process-local caches.

	``id_or_path`` is the HF id or a local path to load directly (a ``Path`` is normalized to ``str`` so it shares
	the same cache slot as its string form). Identical (hf_id, device, dtype, attn, quant, revision, max_memory)
	pairings share the one model object, and the tokenizer is cached by hf_id. Flash-attention is the default with
	automatic fallback to sdpa/eager; quantization is opt-in.

	Parameters:
		id_or_path: HF hub id or a local directory of weights.
		device: either a single placement (``"cuda"``, ``"cuda:1"``, ``"cpu"``, a ``torch.device`` — the default,
			loaded then moved) or a **sharding strategy** handed to ``device_map=``: ``"auto"`` (fill each
			visible GPU in turn, then cpu/disk), ``"balanced"`` (even split over GPUs), ``"balanced_low_0"``
			(leave headroom on GPU 0 for generation buffers), ``"sequential"``, or an explicit
			``{module_name: device}`` map. Use a strategy when the weights do not fit one card — e.g. a 32B
			policy on two 80 GB GPUs; use the single-device default whenever they do, since sharding adds
			cross-device transfers to every forward.
		dtype: parameter dtype; ``bfloat16`` is the default and what every evaluation in this library assumes.
		attn: preferred attention backend, tried first and then degraded through ``sdpa`` and ``eager``, so
			``flash_attention_2`` is safe to leave on hardware/builds that lack it.
		quant: ``None`` (full precision — required for faithful interpretability, since quantization perturbs
			the very activations a probe reads), ``"4bit"`` or ``"8bit"`` via BitsAndBytes when memory forces it.
			Quantized loads place themselves and are never ``.to()``'d.
		revision: pin a specific hub commit/branch/tag; ``None`` takes the default branch.
		max_memory: per-device budget for a ``device_map`` strategy, e.g. ``{0: "70GiB", 1: "70GiB",
			"cpu": "0GiB"}``. Use it to reserve headroom for KV cache and activations, which the automatic map
			does not know about, or to forbid cpu offload (an ``"0GiB"`` cpu entry turns a silent 100x slowdown
			into an out-of-memory error you can act on). Ignored without a strategy.

	Returns:
		``(model, tokenizer)``. On a sharded load, place inputs with
		:func:`~interlens.loading.devices.input_device` rather than ``model.device``.

	Example:
		>>> model, tok = load_model("Qwen/Qwen3-8B")                       # single GPU, bf16, flash-attn
		>>> model, tok = load_model("Qwen/Qwen3-32B", device="balanced",   # two cards, KV headroom reserved
		...                         max_memory={0: "70GiB", 1: "70GiB", "cpu": "0GiB"})
	"""
	hf_id = str(id_or_path)
	tokenizer = cached_tokenizer(hf_id, lambda: load_tokenizer(hf_id, revision=revision))
	# max_memory is a dict (unhashable) and device may be one too, so both are normalized to sorted string
	# tuples: two callers asking for the same budget in a different key order must share one model object, and
	# two asking for DIFFERENT budgets must not.
	weight_key = (hf_id, _hashable(device), str(dtype), attn, quant, revision, _hashable(max_memory))
	model = cached_model(weight_key, lambda: _load_model_weights(hf_id, device, dtype, attn, quant, revision,
	                                                             max_memory))
	return model, tokenizer


def _hashable(value) -> str | tuple:
	"""Normalize a cache-key component that may be a dict (``device_map`` / ``max_memory``) into a stable,
	order-insensitive hashable form; anything else stringifies as before."""
	if isinstance(value, dict):
		return tuple(sorted((str(k), str(v)) for k, v in value.items()))
	return str(value)
