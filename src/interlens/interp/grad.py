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

"""Gradient-enabled forward passes for backprop *through* a model.

The rest of interp is read-only: ``capture_activations`` runs under ``torch.inference_mode`` and detaches, which
is right for logit-lens / probe readouts but throws away the graph. This module is the escape hatch for
optimization *through* a (usually frozen) model: differentiable soft-prompt tuning into a target, and end-to-end
backprop across two stacked models (model A's relaxed tokens feed model B via ``bridge.soft_embed``). Nothing here
touches ``ModelParticipant.generate`` — these are standalone functions on the raw ``.model``, matching the style of
``token_logprobs``/``decoder_layers``.

Two design points:
- Accept ``inputs_embeds`` (soft embeddings) as a first-class input, not just ``input_ids`` — that is how a
  continuous, differentiable signal enters a transformer. Residual-stream capture is grad-connected (via
  ``output_hidden_states`` on the *same* forward, not the separate detached pass ``capture_activations`` uses).
- ``checkpoint=True`` turns on HF gradient checkpointing for the pass, so backprop through a frozen B recomputes
  activations instead of storing them — the memory lever that lets a 0.5B+1.5B two-model stack fit one GPU.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple, TYPE_CHECKING

import torch

from .activation_cache import Site
from .layers import decoder_layers

if TYPE_CHECKING:
	from transformers import PreTrainedModel


@dataclass
class GradCaptureSpec:
	"""What grad-connected activations to pull from ``forward_with_grad`` (mirrors ``CaptureSpec`` minus offload).

	``sites`` is any of ``"residual"``/``"attn"``/``"mlp"``; ``layers`` selects decoder-layer indices (``None`` =
	all). Unlike ``CaptureSpec`` there is no ``offload`` — the whole point is to keep tensors on-device and in the
	autograd graph, so an intermediate-layer objective (e.g. project onto a concept direction) can be backpropagated.
	"""

	sites: tuple[Site, ...] = ("residual",)
	layers: tuple[int, ...] | None = None


class GradForwardOutput(NamedTuple):
	"""Result of ``forward_with_grad``: grad-connected ``logits`` (``[batch, seq, vocab]``) and, if a
	``GradCaptureSpec`` was passed, ``hidden`` mapping ``(site, layer) -> tensor[batch, seq, d_model]`` (also
	grad-connected). ``hidden`` is empty when no capture was requested."""

	logits: torch.Tensor
	hidden: dict[tuple[Site, int], torch.Tensor]


def forward_with_grad(
	model: "PreTrainedModel",
	*,
	input_ids: torch.Tensor | None = None,
	inputs_embeds: torch.Tensor | None = None,
	attention_mask: torch.Tensor | None = None,
	capture: GradCaptureSpec | None = None,
	checkpoint: bool = False,
) -> GradForwardOutput:
	"""One grad-connected forward pass over ``input_ids`` XOR ``inputs_embeds``.

	Exactly one of ``input_ids`` (``[batch, seq]`` long) or ``inputs_embeds`` (``[batch, seq, d_model]`` float,
	typically the output of ``bridge.soft_embed`` or a learnable soft prompt) must be given. ``attention_mask`` is
	optional (``[batch, seq]``). Returns ``logits`` and any requested hidden activations, all still attached to the
	graph so ``.backward()`` flows back to ``inputs_embeds`` / soft-prompt params / an upstream model A.

	``checkpoint=True`` enables HF gradient checkpointing for this call (``use_reentrant=False``) and restores the
	prior setting afterwards; it recomputes layer activations on the backward pass to trade compute for memory, and
	produces identical gradients. Residual sites come from ``output_hidden_states`` (grad-connected); ``attn``/``mlp``
	sites come from non-detaching forward hooks on the submodules.
	"""
	if (input_ids is None) == (inputs_embeds is None):
		raise ValueError("pass exactly one of input_ids or inputs_embeds")

	sites: set[Site] = set(capture.sites) if capture is not None else set()
	need_hidden = "residual" in sites
	need_hooks = bool(sites - {"residual"})  # attn/mlp need submodule hooks; residual comes from hidden_states

	handles = []
	hook_store: dict[tuple[Site, int], torch.Tensor] = {}

	def make_hook(layer_idx: int, site: Site):
		def hook(module, inputs, output):
			hs = output[0] if isinstance(output, tuple) else output
			hook_store[(site, layer_idx)] = hs  # keep grad — do NOT detach
		return hook

	if need_hooks:  # only touch the layer stack when a submodule hook is actually required
		layers = decoder_layers(model)
		hook_layers = capture.layers if capture.layers is not None else tuple(range(len(layers)))
		for li in hook_layers:
			if "attn" in sites:
				handles.append(layers[li].self_attn.register_forward_hook(make_hook(li, "attn")))
			if "mlp" in sites:
				handles.append(layers[li].mlp.register_forward_hook(make_hook(li, "mlp")))

	was_checkpointing = getattr(model, "is_gradient_checkpointing", False)
	try:
		if checkpoint and not was_checkpointing:
			model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
		out = model(
			input_ids=input_ids,
			inputs_embeds=inputs_embeds,
			attention_mask=attention_mask,
			output_hidden_states=need_hidden,
			use_cache=False,
		)
	finally:
		for h in handles:
			h.remove()
		if checkpoint and not was_checkpointing:
			model.gradient_checkpointing_disable()

	hidden: dict[tuple[Site, int], torch.Tensor] = {}
	if need_hidden:
		# hidden_states = (embeddings, layer_0_out, ..., layer_{L-1}_out); layer li output is index li+1.
		hs = out.hidden_states
		want = capture.layers if capture.layers is not None else tuple(range(len(hs) - 1))
		for li in want:
			hidden[("residual", li)] = hs[li + 1]
	hidden.update(hook_store)
	return GradForwardOutput(logits=out.logits, hidden=hidden)


def continuation_logprob(
	model: "PreTrainedModel",
	*,
	target_ids: torch.Tensor,
	prefix_ids: torch.Tensor | None = None,
	prefix_embeds: torch.Tensor | None = None,
	attention_mask: torch.Tensor | None = None,
	reduction: str = "mean",
	checkpoint: bool = False,
) -> torch.Tensor:
	"""Differentiable teacher-forced logprob of ``target_ids`` continuing a prefix, under ``model``.

	The grad-enabled analog of ``train_to_steer/rl_elicit.py::cont_logprob`` (which is ``@torch.no_grad`` and returns
	a float). Supply the prefix as ``prefix_ids`` (``[batch, P]`` long) OR ``prefix_embeds`` (``[batch, P, d_model]``
	float — e.g. a learnable soft prompt, or soft embeddings bridged from model A). ``target_ids`` is ``[batch, T]``
	long (or ``[T]`` broadcast to batch 1). The prefix and target are embedded via ``model.get_input_embeddings()``
	and run in one forward; the returned scalar (or per-example vector, see ``reduction``) is the logprob the model
	assigns to the exact target tokens, still attached to the graph.

	``reduction``: ``"mean"`` (mean over target tokens, mean over batch -> scalar; the reward used by rl_elicit),
	``"sum"`` (sum over target tokens, mean over batch), or ``"none"`` (``[batch, T]`` per-token logprobs). Use
	``"mean"`` as a length-normalized elicitation reward, ``"sum"`` when total sequence likelihood matters, ``"none"``
	for custom weighting. ``checkpoint`` is forwarded to save memory when backpropagating through a large frozen B.
	"""
	if (prefix_ids is None) == (prefix_embeds is None):
		raise ValueError("pass exactly one of prefix_ids or prefix_embeds")
	embed = model.get_input_embeddings()
	device = embed.weight.device
	if target_ids.dim() == 1:
		target_ids = target_ids.unsqueeze(0)
	target_ids = target_ids.to(device)

	if prefix_embeds is None:
		if prefix_ids.dim() == 1:
			prefix_ids = prefix_ids.unsqueeze(0)
		prefix_embeds = embed(prefix_ids.to(device))
	prefix_embeds = prefix_embeds.to(device)
	if prefix_embeds.shape[0] == 1 and target_ids.shape[0] > 1:
		prefix_embeds = prefix_embeds.expand(target_ids.shape[0], -1, -1)

	target_embeds = embed(target_ids)
	full = torch.cat([prefix_embeds, target_embeds], dim=1)
	fout = forward_with_grad(model, inputs_embeds=full, attention_mask=attention_mask, checkpoint=checkpoint)

	P = prefix_embeds.shape[1]
	T = target_ids.shape[1]
	# Logits at position i predict token i+1; the T target tokens sit at positions P..P+T-1, so the logits that
	# predict them are at positions P-1..P+T-2.
	pred_logits = fout.logits[:, P - 1: P + T - 1, :].float()
	logp = torch.log_softmax(pred_logits, dim=-1)
	tok_logp = logp.gather(2, target_ids.unsqueeze(2)).squeeze(2)  # [batch, T]

	if reduction == "none":
		return tok_logp
	if reduction == "sum":
		return tok_logp.sum(dim=1).mean()
	if reduction == "mean":
		return tok_logp.mean()
	raise ValueError(f"unknown reduction {reduction!r}")
