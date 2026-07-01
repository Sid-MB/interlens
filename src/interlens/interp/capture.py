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

from dataclasses import dataclass
from typing import NamedTuple, TYPE_CHECKING

import torch

if TYPE_CHECKING:
	from transformers import PreTrainedModel

from .activation_cache import ActivationCache, CaptureSpec, Site
from .layers import decoder_layers


class CapturedSite(NamedTuple):
	"""One activation captured by ``capture_activations``: the ``tensor`` (``[seq, d_model]``) at a given
	``layer`` and ``site``. A lightweight typed row (unpacks like the old ``(layer, site, tensor)`` tuple) that
	the participant folds into a fully-tagged ``ActivationRecord``."""

	layer: int
	site: Site
	tensor: torch.Tensor


@dataclass
class CaptureRequest:
	"""A pending capture handed to ``generate``: where to store records (``cache``) and what to grab (``spec``).

	The ``Conversation`` builds this (via ``conv.capture(...)``) and the participant fills the cache with records
	tagged by participant + turn, so the caller ends up with structurally-tagged activations."""

	cache: ActivationCache
	spec: CaptureSpec


def capture_activations(model: "PreTrainedModel", input_ids: torch.Tensor, spec: CaptureSpec) -> list[CapturedSite]:
	"""Run one clean forward pass over ``input_ids`` and return ``[(layer, site, tensor[seq, d_model])]``.

	Design choice: capture is a *separate forward pass* over the full (prompt + generated) sequence rather than
	accumulating hooks across the multi-step decode loop. This is simpler and provably complete — every position
	is present in one pass — at the cost of one extra forward. Residual-stream activations come from
	``output_hidden_states`` (no hooks needed); ``attn``/``mlp`` sublayer outputs come from forward hooks on the
	corresponding submodules.

	Note: ``attn`` captures the attention *sublayer output* (post-o_proj), which is available under any attention
	backend. Attention *weights/patterns* are NOT captured here — those require ``attn_implementation='eager'`` +
	``output_attentions`` and are out of scope for the default kernel.
	"""
	layers = decoder_layers(model)
	want = spec.layers if spec.layers is not None else tuple(range(len(layers)))
	sites = set(spec.sites)

	results: list[CapturedSite] = []
	handles = []
	hook_store: dict[tuple[int, Site], torch.Tensor] = {}

	def make_hook(layer_idx: int, site: Site):
		def hook(module, inputs, output):
			hs = output[0] if isinstance(output, tuple) else output
			hook_store[(layer_idx, site)] = hs.detach()[0]  # [seq, d_model]
		return hook

	for li in want:
		if "attn" in sites:
			handles.append(layers[li].self_attn.register_forward_hook(make_hook(li, "attn")))
		if "mlp" in sites:
			handles.append(layers[li].mlp.register_forward_hook(make_hook(li, "mlp")))

	need_hidden = "residual" in sites
	try:
		with torch.inference_mode():
			out = model(input_ids, output_hidden_states=need_hidden, use_cache=False)
	finally:
		for h in handles:
			h.remove()

	if need_hidden:
		# hidden_states is (embeddings, layer_0_out, ..., layer_{L-1}_out); layer li output is index li+1.
		hs = out.hidden_states
		for li in want:
			results.append(CapturedSite(li, "residual", hs[li + 1][0]))
	for (li, site), tensor in hook_store.items():
		results.append(CapturedSite(li, site, tensor))

	return results
