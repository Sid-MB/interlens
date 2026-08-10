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

# [implement: rational_agents new transformer feature] 2026-08-01

"""Virtual (soft) tokens inside ordinary text prompts, plus the message-span read path that pairs with them.

Two utilities that together make a *continuous* channel into an otherwise text-only chat harness:

- :class:`VirtualTokenInjector` — write soft tokens into a prompt **without** an ``inputs_embeds`` code path. The
  harness's batched generation (``ModelParticipant.generate_batch``) chat-templates strings and calls
  ``model.generate(input_ids=...)``; it cannot accept embeddings. So the injector hands you a *placeholder text
  snippet* (a run of one existing rare vocab token, repeated ``n_soft`` times — no new tokens, no embedding resize)
  to render into the prompt like any other text, and a context manager that swaps the embeddings at exactly those
  positions for caller-supplied vectors. The swap is a forward-pre-hook (to see ``input_ids``) plus a forward hook
  (to edit the embedding output) on ``model.get_input_embeddings()``, so it works identically under
  ``model.generate`` (placeholders live in the prefill only; cached decode steps pass through untouched) and under a
  plain ``model(...)`` training forward, and it is autograd-transparent: gradients flow back into the vectors, so
  the vectors can come from a trainable :class:`~interlens.interp.bridge.LinearBridge`.

- :func:`span_pooled_residuals` — the matching read path: one pooled residual vector *per message* of a rendered
  conversation, by combining ``capture_activations`` / ``forward_with_grad`` with ``routing.message_token_spans``
  and ``pooling.span_pool`` (which owns the pooling arithmetic). This is what a theory-of-mind probe head reads.

Worked example (bridge a partner's hidden state into a listener's prompt as 4 soft tokens)::

	from interlens.interp import VirtualTokenInjector, span_pooled_residuals, LinearBridge

	inj = VirtualTokenInjector(tok_b, n_soft=4)
	pooled = span_pooled_residuals(model_a, tok_a, view, layers=(-1,), grad=True)   # [n_messages, d_a]
	vectors = bridge(pooled[("residual", -1)][-1:].unsqueeze(0))                    # [1, 4, d_b] (after a reshape)
	prompt = f"Partner state: {inj.text}\nWhat do they want?"
	with inj.inject(model_b, vectors):
		out = model_b.generate(**tok_b(prompt, return_tensors="pt"), max_new_tokens=16)
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, Iterator, TYPE_CHECKING

import torch

from ..loading.devices import input_device
from .activation_cache import CaptureSpec, Site
from .capture import capture_activations
from .grad import GradCaptureSpec, forward_with_grad
from .pooling import Pool, span_pool
from .routing import message_token_spans

if TYPE_CHECKING:
	from transformers import PreTrainedModel, PreTrainedTokenizerBase

# Substrings that mark a vocab entry as a reserved/unused slot — the safest placeholders, since a well-formed
# conversation never contains them and no chat template emits them. Tried in this order before anything else.
_RESERVED_HINTS = ("reserved", "unused", "extra_id", "fim_pad", "<pad>", "vision_pad", "object_ref")


class VirtualTokenInjector:
	"""Reserve ``n_soft`` positions in a *text* prompt and substitute their input embeddings at forward time.

	Construction picks (and validates) a ``placeholder`` token from ``tokenizer``'s existing vocabulary — no
	``add_special_tokens``, no ``resize_token_embeddings``, so the model is untouched and any checkpoint stays
	loadable. Validation is empirical, not assumed: the candidate must (a) tokenize, repeated ``n_soft`` times with
	no separator, to exactly ``n_soft`` copies of its own id, and (b) survive ``apply_chat_template`` — rendered
	inside a user message the run must still appear exactly once, contiguous, at length ``n_soft``. Templates that
	escape or normalize the candidate are rejected and the next candidate is tried.

	Use :attr:`text` as the snippet to splice into your prompt string, then wrap the forward/generate call in
	:meth:`inject` (or register/remove hooks yourself with :meth:`register`, the ``SteeringSpec.register``
	convention).

	Args:
		tokenizer: the tokenizer of the model that will consume the prompt; supplies the vocab and chat template.
		n_soft: how many virtual token positions to reserve (the ``vectors`` you inject are ``[B, n_soft, d]``).
		placeholder: force a specific placeholder token *string* (must exist in the vocab and pass validation).
			Leave ``None`` to auto-pick a reserved/unused token — pass one explicitly only when you need the
			rendered prompt to be human-readable or stable across tokenizer versions.
	"""

	def __init__(self, tokenizer: "PreTrainedTokenizerBase", n_soft: int, placeholder: str | None = None):
		if n_soft < 1:
			raise ValueError(f"n_soft must be >= 1, got {n_soft}")
		self.tokenizer = tokenizer
		self.n_soft = int(n_soft)
		self.placeholder = self._pick_placeholder(tokenizer, self.n_soft, placeholder)
		self.token_id = int(tokenizer.convert_tokens_to_ids(self.placeholder))

	@property
	def text(self) -> str:
		"""The snippet to render into a prompt: the placeholder token repeated ``n_soft`` times, no separators."""
		return self.placeholder * self.n_soft

	def __repr__(self) -> str:
		return f"VirtualTokenInjector(placeholder={self.placeholder!r}, id={self.token_id}, n_soft={self.n_soft})"

	# -- placeholder selection -------------------------------------------------------------------------------

	@staticmethod
	def _candidates(tokenizer: "PreTrainedTokenizerBase") -> list[str]:
		"""Placeholder candidates, best first: reserved/unused added tokens, then any other added token."""
		added = list(getattr(tokenizer, "added_tokens_encoder", {}) or {})
		if not added:
			added = list(tokenizer.all_special_tokens)
		reserved = [t for t in added if any(h in t.lower() for h in _RESERVED_HINTS)]
		return reserved + [t for t in added if t not in reserved]

	@classmethod
	def _pick_placeholder(cls, tokenizer: "PreTrainedTokenizerBase", n_soft: int, forced: str | None) -> str:
		cands = [forced] if forced is not None else cls._candidates(tokenizer)
		for cand in cands:
			if cls._validate(tokenizer, cand, n_soft):
				return cand
		raise ValueError(
			f"no placeholder token round-trips through this tokenizer's chat template as {n_soft} contiguous ids"
			+ (f" (forced placeholder {forced!r} failed)" if forced is not None else f" (tried {len(cands)} candidates)")
		)

	@staticmethod
	def _validate(tokenizer: "PreTrainedTokenizerBase", cand: str, n_soft: int) -> bool:
		"""True iff ``cand * n_soft`` tokenizes to exactly ``n_soft`` copies of ``cand``'s id, both bare and after
		``apply_chat_template`` wraps it in a user message with text on either side."""
		tid = tokenizer.convert_tokens_to_ids(cand)
		unk = getattr(tokenizer, "unk_token_id", None)
		if tid is None or (unk is not None and tid == unk):
			return False
		snippet = cand * n_soft
		if list(tokenizer(snippet, add_special_tokens=False).input_ids) != [tid] * n_soft:
			return False
		try:
			rendered = tokenizer.apply_chat_template(
				[{"role": "user", "content": f"before {snippet} after"}], tokenize=False, add_generation_prompt=True
			)
		except Exception:
			return False
		ids = list(tokenizer(rendered, add_special_tokens=False).input_ids)
		return ids.count(tid) == n_soft and _find_run(ids, tid, n_soft) is not None

	# -- injection -------------------------------------------------------------------------------------------

	def run_starts(self, input_ids: torch.Tensor) -> list[int | None]:
		"""Per batch row, the index where the placeholder run starts, or ``None`` if that row has no placeholders.

		Raises if a row holds a partial or non-contiguous run — that means the prompt was built wrong (e.g. the
		snippet got split by a template) and silently steering the wrong positions would be worse than failing.
		"""
		if input_ids.dim() != 2:
			raise ValueError(f"expected [batch, seq] input_ids, got shape {tuple(input_ids.shape)}")
		starts: list[int | None] = []
		for row in input_ids.tolist():
			count = row.count(self.token_id)
			if count == 0:
				starts.append(None)
				continue
			start = _find_run(row, self.token_id, self.n_soft)
			if start is None or count != self.n_soft:
				raise ValueError(
					f"row holds {count} placeholder token(s) but not one contiguous run of {self.n_soft}"
				)
			starts.append(start)
		return starts

	def register(self, model: "PreTrainedModel", vectors: torch.Tensor) -> list:
		"""Register the substitution hooks on ``model`` and return the handles (caller removes them; or use
		:meth:`inject`, which does that for you).

		``vectors`` is ``[batch, n_soft, d_model]``, aligned row-for-row with the ``input_ids`` the model will see;
		a ``batch`` of 1 is broadcast to every row. It is *not* detached and *not* copied into the graph in place,
		so ``loss.backward()`` reaches it (and anything upstream, e.g. a ``LinearBridge``). Rows whose ids contain
		no placeholder keep their ordinary token embeddings.

		Mechanics: a forward-**pre**-hook on ``model.get_input_embeddings()`` records the ``input_ids`` that call is
		about to embed (the post-hook only sees the output), and the forward hook returns a modified clone with the
		placeholder slice overwritten. Decode steps under a KV cache pass one non-placeholder token and are no-ops.
		"""
		if vectors.dim() != 3 or vectors.shape[1] != self.n_soft:
			raise ValueError(f"vectors must be [batch, {self.n_soft}, d_model], got {tuple(vectors.shape)}")
		embed = model.get_input_embeddings()
		seen: dict[str, torch.Tensor | None] = {"ids": None}

		def pre_hook(module, args, kwargs):
			ids = args[0] if args else kwargs.get("input")
			seen["ids"] = ids if isinstance(ids, torch.Tensor) else None

		def post_hook(module, args, output):
			ids = seen["ids"]
			if ids is None or ids.dim() != 2:
				return output
			starts = self.run_starts(ids)
			if all(s is None for s in starts):
				return output
			vecs = vectors.to(dtype=output.dtype, device=output.device)
			out = output.clone()  # differentiable copy: in-place writes below stay autograd-safe
			for b, start in enumerate(starts):
				if start is None:
					continue
				out[b, start:start + self.n_soft] = vecs[b if vecs.shape[0] > 1 else 0]
			return out

		return [embed.register_forward_pre_hook(pre_hook, with_kwargs=True),
		        embed.register_forward_hook(post_hook)]

	@contextmanager
	def inject(self, model: "PreTrainedModel", vectors: torch.Tensor) -> Iterator["VirtualTokenInjector"]:
		"""Context manager around :meth:`register`: hooks are removed on exit, including on exception."""
		handles = self.register(model, vectors)
		try:
			yield self
		finally:
			for h in handles:
				h.remove()


def _find_run(ids: list[int], token_id: int, length: int) -> int | None:
	"""Start index of the first run of exactly ``length`` consecutive ``token_id`` in ``ids``, else ``None``."""
	for i in range(len(ids) - length + 1):
		if all(ids[i + j] == token_id for j in range(length)):
			return i
	return None


def span_pooled_residuals(
	model: "PreTrainedModel",
	tokenizer: "PreTrainedTokenizerBase",
	view: list[dict],
	*,
	layers: int | Iterable[int] | None,
	sites: tuple[Site, ...] = ("residual",),
	pool: Pool = "mean",
	grad: bool = False,
) -> dict[tuple[Site, int], torch.Tensor]:
	"""One pooled activation vector **per message** of ``view``, at each requested site/layer.

	Renders ``view`` once with the chat template, locates each message's token span with
	``routing.message_token_spans`` (prefix-diffing the rendered strings, so spans include each message's role
	markup), runs a single forward pass, and pools each span down to one vector. Returns
	``{(site, layer): tensor[n_messages, d_model]}`` — keyed like ``forward_with_grad``'s ``hidden``.

	Args:
		model: the model to read; must accept ``input_ids`` (no generation happens here).
		tokenizer: supplies the chat template used for both the render and the spans.
		view: the conversation as chat-template dicts (``[{"role": ..., "content": ...}, ...]``).
		layers: decoder-layer index, iterable of indices, or ``None`` for every layer. Negative indices count from
			the end (``-1`` = last layer), so ``layers=(-1,)`` is "the usual readout layer" without knowing depth.
		sites: any of ``"residual"``/``"attn"``/``"mlp"``. ``"residual"`` is the probe default; the sublayer sites
			are there when you want to attribute a readout to attention vs MLP.
		pool: ``"mean"`` or ``"last"``, forwarded to :func:`~interlens.interp.pooling.span_pool` — mean averages the
			span's tokens (stable, order-insensitive; the probe default), last takes the span's final token (the
			position that causally sees the whole message, and what a next-token readout conditions on).
		grad: ``False`` runs the detached ``capture_activations`` pass (cheap, inference-mode) — right for fitting a
			probe on frozen features. ``True`` routes through ``forward_with_grad`` so the pooled vectors stay in the
			autograd graph — required when they feed a trainable bridge/soft prompt that is optimized end to end.
	"""
	spans = message_token_spans(tokenizer, view)
	rendered = tokenizer.apply_chat_template(view, tokenize=False)
	ids = tokenizer(rendered, add_special_tokens=False, return_tensors="pt").input_ids
	ids = ids.to(input_device(model))

	n_layers = len(model.model.layers) if hasattr(model, "model") else model.config.num_hidden_layers
	want = tuple(range(n_layers)) if layers is None else ((layers,) if isinstance(layers, int) else tuple(layers))
	want = tuple(li % n_layers for li in want)

	acts: dict[tuple[Site, int], torch.Tensor] = {}
	if grad:
		out = forward_with_grad(model, input_ids=ids, capture=GradCaptureSpec(sites=tuple(sites), layers=want))
		acts = {k: v[0] for k, v in out.hidden.items()}  # [batch=1, seq, d] -> [seq, d]
	else:
		for cap in capture_activations(model, ids, CaptureSpec(sites=tuple(sites), layers=want, offload=None)):
			acts[(cap.site, cap.layer)] = cap.tensor

	return {key: span_pool(tensor, spans, mode=pool) for key, tensor in acts.items()}
