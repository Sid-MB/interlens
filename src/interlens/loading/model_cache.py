# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import gc

import torch

# Two SEPARATE process-local caches, so different-size same-family models share the tokenizer while keeping
# their own weights. This is the concrete "don't redo unnecessary work" optimization:
#
#  - weight cache: keyed by (hf_id, device, dtype, attn, quant) — weights are per-size (2b and 9b load
#    separately; weights and KV caches are genuinely not shareable across sizes).
#  - tokenizer cache: keyed by tokenizer_id — device-independent, so gemma2-2b and gemma2-9b talking to each
#    other load the Gemma tokenizer ONCE and both participants reference the same object.
_WEIGHTS: dict[tuple, object] = {}
_TOKENIZERS: dict[str, object] = {}


def cached_model(key: tuple, loader):
	model = _WEIGHTS.get(key)
	if model is None:
		model = _WEIGHTS[key] = loader()
	return model


def cached_tokenizer(tok_id: str, loader):
	tokenizer = _TOKENIZERS.get(tok_id)
	if tokenizer is None:
		tokenizer = _TOKENIZERS[tok_id] = loader()
	return tokenizer


def free() -> None:
	"""Drop both caches and reclaim GPU memory. Useful between phases that load many models in one process."""
	_WEIGHTS.clear()
	_TOKENIZERS.clear()
	gc.collect()
	if torch.cuda.is_available():
		torch.cuda.empty_cache()
