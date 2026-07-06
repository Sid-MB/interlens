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

"""Mixture-of-Experts routing capture and statistics.

Reads *which experts an MoE model routes each token to* — the discrete, cheap-to-interpret counterpart of
residual-stream capture. Like ``capture_activations``, capture is a single clean forward pass over the full
token sequence (provably complete, one extra forward) rather than hooks accumulated across a decode loop: both
``OlmoeForCausalLM`` and ``Qwen3MoeForCausalLM`` (and other HF MoE families) return per-MoE-layer router logits
natively via ``output_router_logits=True``, so no module hooks are needed at all.

Typical use: replay a saved conversation view through the MoE, get per-token routing with
``capture_router_logits``, compute per-message expert-usage distributions with ``routing_stats`` restricted to
``message_token_spans``, and compare conditions with ``js_divergence`` / ``topk_expert_overlap``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple, TYPE_CHECKING

import torch

if TYPE_CHECKING:
	from transformers import PreTrainedModel, PreTrainedTokenizerBase

from .layers import decoder_layers


def moe_num_experts(model: "PreTrainedModel") -> int:
	"""Number of routed experts per MoE layer (``config.num_experts`` — same field name in OLMoE/Qwen-MoE)."""
	return int(model.config.num_experts)


def moe_topk(model: "PreTrainedModel") -> int:
	"""Experts selected per token (``config.num_experts_per_tok``)."""
	return int(model.config.num_experts_per_tok)


def moe_layer_indices(model: "PreTrainedModel") -> tuple[int, ...]:
	"""Decoder-layer indices that carry a sparse MoE block.

	HF MoE models return ``router_logits`` only for the *sparse* layers, in layer order, with no index
	attached. This maps that tuple back to real decoder-layer indices by checking each layer's ``mlp`` for a
	router ``gate`` submodule — which handles mixed stacks (e.g. Qwen-MoE ``decoder_sparse_step`` /
	``mlp_only_layers`` leaving some layers dense) as well as fully-sparse stacks like OLMoE.
	"""
	idx = []
	for i, layer in enumerate(decoder_layers(model)):
		mlp = getattr(layer, "mlp", None)
		if mlp is not None and hasattr(mlp, "gate") and hasattr(mlp, "experts"):
			idx.append(i)
	if not idx:
		raise ValueError(f"{type(model).__name__} has no sparse MoE layers (no mlp.gate/mlp.experts found)")
	return tuple(idx)


class RoutingCapture(NamedTuple):
	"""Per-token routing at one MoE layer, from one ``capture_router_logits`` pass.

	``router_logits`` is the raw pre-softmax gate output ``[seq, n_experts]`` (cpu fp32), or ``None`` when the
	capture was compacted with ``top_k_only=True``. ``topk_experts`` / ``topk_probs`` are always present: the
	``k`` selected expert ids (int16) and their softmax router probabilities (fp16), ``[seq, k]`` each.
	"""

	layer: int
	router_logits: torch.Tensor | None
	topk_experts: torch.Tensor
	topk_probs: torch.Tensor


def capture_router_logits(model: "PreTrainedModel", input_ids: torch.Tensor, layers: tuple[int, ...] | None = None,
                          top_k_only: bool = False, offload: str = "cpu") -> list[RoutingCapture]:
	"""One clean forward pass over ``input_ids`` (``[1, seq]``); return per-MoE-layer ``RoutingCapture``.

	Parameters:
		model: an HF MoE causal LM whose ``forward`` accepts ``output_router_logits=True`` (OLMoE, Qwen-MoE,
			Mixtral, ...).
		input_ids: full token sequence to route, shape ``[1, seq]`` (batch of 1 — replay one view at a time).
		layers: decoder-layer indices to keep (default: all sparse layers, per ``moe_layer_indices``).
		top_k_only: drop the full ``[seq, n_experts]`` logits and keep only top-k ids/probs (int16/fp16,
			~8x smaller — use for long-sequence sweeps over large MoEs like Qwen3-30B-A3B).
		offload: device for the returned tensors (default ``"cpu"`` so GPU memory is freed immediately).
	"""
	sparse = moe_layer_indices(model)
	want = set(layers if layers is not None else sparse)
	k = moe_topk(model)

	with torch.inference_mode():
		out = model(input_ids.to(model.device), output_router_logits=True, use_cache=False)
	if getattr(out, "router_logits", None) is None:
		raise ValueError(f"{type(model).__name__} did not return router_logits — not an MoE forward?")

	results: list[RoutingCapture] = []
	for layer_idx, logits in zip(sparse, out.router_logits):
		if layer_idx not in want:
			continue
		logits = logits.detach().float()  # [seq, n_experts] (HF flattens batch=1 into seq)
		if logits.dim() == 3:
			logits = logits[0]
		probs = torch.softmax(logits, dim=-1)
		topk_probs, topk_ids = probs.topk(k, dim=-1)
		results.append(RoutingCapture(
			layer=layer_idx,
			router_logits=None if top_k_only else logits.to(offload),
			topk_experts=topk_ids.to(torch.int16).to(offload),
			topk_probs=topk_probs.to(torch.float16).to(offload),
		))
	return results


@dataclass
class RoutingStats:
	"""Aggregate expert-usage distributions over a set of token positions.

	``expert_load[l, e]`` is the fraction of top-k selections at layer ``l`` that went to expert ``e``
	(rows sum to 1 — the discrete "which experts fired" histogram). ``expert_mass[l, e]`` is the mean softmax
	router probability (``None`` if the captures were ``top_k_only`` — full logits are needed for mass).
	``layers`` are the decoder-layer indices of the rows; ``n_tokens`` is how many positions were pooled.
	"""

	expert_load: torch.Tensor
	expert_mass: torch.Tensor | None
	layers: tuple[int, ...]
	n_tokens: int
	top_k: int


def routing_stats(captures: list[RoutingCapture], n_experts: int,
                  spans: list[tuple[int, int]] | None = None) -> RoutingStats:
	"""Pool per-token routing into per-layer expert-usage distributions.

	Parameters:
		captures: output of ``capture_router_logits`` (all layers share one token sequence).
		n_experts: total routed experts (``moe_num_experts(model)``) — needed to size the histogram since a
			span may never touch some experts.
		spans: optional ``[(start, end), ...]`` token windows to restrict to (e.g. only the MoE's own generated
			messages, from ``message_token_spans``). Default: all positions.
	"""
	if not captures:
		raise ValueError("no captures given")
	seq = captures[0].topk_experts.shape[0]
	mask = torch.zeros(seq, dtype=torch.bool)
	if spans is None:
		mask[:] = True
	else:
		for s, e in spans:
			mask[s:e] = True
	n_tok = int(mask.sum())
	if n_tok == 0:
		raise ValueError(f"spans select zero tokens (seq={seq}, spans={spans})")

	k = captures[0].topk_experts.shape[1]
	load = torch.zeros(len(captures), n_experts)
	mass = torch.zeros(len(captures), n_experts) if captures[0].router_logits is not None else None
	for li, cap in enumerate(captures):
		ids = cap.topk_experts[mask].long().reshape(-1)                       # [n_tok * k]
		load[li] = torch.bincount(ids, minlength=n_experts).float() / ids.numel()
		if mass is not None:
			mass[li] = torch.softmax(cap.router_logits[mask], dim=-1).mean(0)
	return RoutingStats(expert_load=load, expert_mass=mass, layers=tuple(c.layer for c in captures),
	                    n_tokens=n_tok, top_k=k)


def kl_divergence(p: torch.Tensor, q: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
	"""Per-layer KL(p || q) between expert distributions ``[n_layers, n_experts]`` → ``[n_layers]``."""
	p = p + eps
	q = q + eps
	p = p / p.sum(-1, keepdim=True)
	q = q / q.sum(-1, keepdim=True)
	return (p * (p / q).log()).sum(-1)


def js_divergence(p: torch.Tensor, q: torch.Tensor) -> torch.Tensor:
	"""Per-layer Jensen–Shannon divergence (symmetric, bounded by ln 2) → ``[n_layers]``."""
	m = 0.5 * (p + q)
	return 0.5 * kl_divergence(p, m) + 0.5 * kl_divergence(q, m)


def topk_expert_overlap(p: torch.Tensor, q: torch.Tensor, k: int = 8) -> torch.Tensor:
	"""Per-layer fraction of overlap between the ``k`` most-used experts of ``p`` and of ``q`` → ``[n_layers]``."""
	pi = p.topk(k, dim=-1).indices
	qi = q.topk(k, dim=-1).indices
	out = torch.zeros(p.shape[0])
	for li in range(p.shape[0]):
		out[li] = len(set(pi[li].tolist()) & set(qi[li].tolist())) / k
	return out


def message_token_spans(tokenizer: "PreTrainedTokenizerBase", view: list[dict]) -> list[tuple[int, int]]:
	"""Token span ``(start, end)`` of each message of ``view`` in the fully-rendered chat-template sequence.

	Method: render the *string* prefixes ``apply_chat_template(view[:i], tokenize=False)`` for each ``i`` and
	require each to be a string-prefix of the next (raised on non-prefix-stable templates). The full string is
	then tokenized **once** with ``return_offsets_mapping=True`` and each char boundary is mapped to the first
	token whose offset starts at/after it — prefix *strings* are never tokenized independently, because a
	tokenization of a prefix string is not in general a prefix of the full tokenization.

	Note this describes the final replayed view (the whole conversation templated once). Live generation builds
	the sequence incrementally, but for standard chat templates the rendered text is identical, so spans match.
	The returned spans cover each message's rendered chunk *including* its role header/footer markup.
	"""
	renders = [tokenizer.apply_chat_template(view[:i], tokenize=False) for i in range(1, len(view) + 1)]
	for a, b in zip(renders, renders[1:]):
		if not b.startswith(a):
			raise ValueError("chat template is not prefix-stable; cannot compute message spans by prefix diffing")
	full = renders[-1]
	enc = tokenizer(full, return_offsets_mapping=True, add_special_tokens=False)
	starts = [off[0] for off in enc["offset_mapping"]]
	n = len(starts)

	def tok_at(char_pos: int) -> int:
		for ti in range(n):
			if starts[ti] >= char_pos:
				return ti
		return n

	bounds = [0] + [len(r) for r in renders]
	return [(tok_at(bounds[i]), tok_at(bounds[i + 1])) for i in range(len(view))]
