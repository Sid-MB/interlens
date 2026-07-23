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

import gc
import threading

import torch

# Two SEPARATE process-local caches, so different-size same-family models share the tokenizer while keeping
# their own weights. This is the concrete "don't redo unnecessary work" optimization:
#
#  - weight cache: keyed by (hf_id, device, dtype, attn, quant) — weights are per-size (2b and 9b load
#    separately; weights and KV caches are genuinely not shareable across sizes).
#  - tokenizer cache: keyed by hf_id — device-independent, so two participants on the same model load its
#    tokenizer ONCE and both reference the same object.
_WEIGHTS: dict[tuple, object] = {}
_TOKENIZERS: dict[str, object] = {}

# Per-key load locks. Concurrent rollouts (the async ``EpisodePool``, the multi-GPU runner) can have several
# worker threads request the SAME uncached key at once; without serialization each runs the loader, and a
# ``transformers`` meta-device load + ``.to(device)`` is not thread-safe when run concurrently — the observed
# failure is "Cannot copy out of meta tensor; no data!" as one thread's ``.to()`` races another's still-on-meta
# weights. A per-key lock (double-checked below) makes exactly ONE thread run the loader while the others block
# until the object is fully materialized; distinct keys still load in parallel (only same-key loads serialize).
# ``_REGISTRY_LOCK`` guards the tiny lock-registry dicts themselves.
_WEIGHT_LOCKS: dict[tuple, threading.Lock] = {}
_TOKENIZER_LOCKS: dict[str, threading.Lock] = {}
_REGISTRY_LOCK = threading.Lock()


def _key_lock(locks: dict, key) -> threading.Lock:
	"""The lock for ``key``, created once under the registry lock (so two threads racing on a brand-new key still
	agree on the same lock object)."""
	with _REGISTRY_LOCK:
		lock = locks.get(key)
		if lock is None:
			lock = locks[key] = threading.Lock()
		return lock


def cached_model(key: tuple, loader):
	"""Return the cached model for ``key``, running ``loader()`` at most once even under concurrent callers.

	Double-checked locking: the fast path is a lock-free ``dict.get`` (atomic under the GIL) once the model is
	cached; a miss takes the per-key lock and re-checks, so the loader runs exactly once and every caller gets
	the same fully-materialized object. The key is published only AFTER ``loader()`` returns, so no thread ever
	observes a partially-``.to()``'d model."""
	model = _WEIGHTS.get(key)
	if model is not None:
		return model
	with _key_lock(_WEIGHT_LOCKS, key):
		model = _WEIGHTS.get(key)
		if model is None:
			model = _WEIGHTS[key] = loader()
		return model


def cached_tokenizer(tok_id: str, loader):
	"""Return the cached tokenizer for ``tok_id``, running ``loader()`` at most once even under concurrent
	callers (same double-checked per-key locking as :func:`cached_model`)."""
	tokenizer = _TOKENIZERS.get(tok_id)
	if tokenizer is not None:
		return tokenizer
	with _key_lock(_TOKENIZER_LOCKS, tok_id):
		tokenizer = _TOKENIZERS.get(tok_id)
		if tokenizer is None:
			tokenizer = _TOKENIZERS[tok_id] = loader()
		return tokenizer


def free() -> None:
	"""Drop both caches and reclaim GPU memory. Useful between phases that load many models in one process."""
	_WEIGHTS.clear()
	_TOKENIZERS.clear()
	with _REGISTRY_LOCK:
		_WEIGHT_LOCKS.clear()
		_TOKENIZER_LOCKS.clear()
	gc.collect()
	if torch.cuda.is_available():
		torch.cuda.empty_cache()
