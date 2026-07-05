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

"""Differentiable bridges for feeding one model's output into another's input.

Text is a non-differentiable bottleneck: sampling a discrete token from model A kills the gradient before it can
reach B. These utilities replace the sampled token with a *continuous relaxation* that B can consume as soft
embeddings, so a loss on B backpropagates all the way into A. Two regimes:

- **Shared tokenizer (vocab mixture):** ``soft_embed`` turns a distribution over A's vocab (optionally relaxed via
  ``gumbel_softmax_tokens``) into an embedding in B's space by mixing B's embedding rows. Exact when the tokenizers
  match; ``soft_embed(B, one_hot(ids))`` equals ``B``'s ordinary token embedding of ``ids``.
- **Different tokenizers (learned adapter):** ``LinearBridge`` maps A's hidden state (``d_a``) into B's embedding
  space (``d_b``), sidestepping the vocab mismatch — the same shape of cross-model linear map used in the
  Procrustes/CKA analyses, but here trained jointly against B's downstream loss.

Pair these with ``grad.forward_with_grad`` / ``grad.continuation_logprob`` (which accept ``inputs_embeds``) to close
the A -> B loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch
import torch.nn.functional as F
from torch import nn

if TYPE_CHECKING:
	from transformers import PreTrainedModel


def soft_embed(model: "PreTrainedModel", probs: torch.Tensor) -> torch.Tensor:
	"""Mix ``model``'s input-embedding rows by a per-position distribution: ``[..., V] @ E[V, d] -> [..., d]``.

	``probs`` is a (relaxed or one-hot) distribution over ``model``'s vocab for each position — e.g. a softmax /
	``gumbel_softmax_tokens`` output of an upstream model. Returns grad-connected soft embeddings suitable to pass as
	``inputs_embeds`` to ``forward_with_grad`` / ``continuation_logprob``. This is exact for hard one-hots: feeding
	``one_hot(ids)`` reproduces ``model.get_input_embeddings()(ids)``.
	"""
	weight = model.get_input_embeddings().weight  # [V, d]
	return probs.to(dtype=weight.dtype, device=weight.device) @ weight


def gumbel_softmax_tokens(logits: torch.Tensor, tau: float = 1.0, hard: bool = False) -> torch.Tensor:
	"""Relaxed (Gumbel-softmax) sample over the last (vocab) dim of ``logits``, differentiable in ``logits``.

	``tau`` is the temperature: high -> smooth mixture (biased but low-variance gradients), low -> near-one-hot
	(faithful to discrete sampling but higher-variance). Anneal ``tau`` down over training to move from an easy soft
	optimization toward the discrete tokens B will actually see. ``hard=True`` uses the straight-through estimator: a
	true one-hot on the forward pass, softmax gradient on the backward pass — so the value B consumes is a real token
	while gradients still flow. Returns ``[..., V]`` to feed straight into ``soft_embed``.
	"""
	return F.gumbel_softmax(logits, tau=tau, hard=hard, dim=-1)


class LinearBridge(nn.Module):
	"""Learned linear map from model A's hidden width ``d_a`` to model B's embedding width ``d_b``.

	For heterogeneous (different-tokenizer) pairs where a vocab mixture is undefined: take A's last-layer hidden
	states (via ``forward_with_grad(..., capture=GradCaptureSpec(sites=('residual',), layers=(last,)))``), map them
	into B's embedding space, and pass the result as ``inputs_embeds`` to B. Trained jointly with A against B's loss.
	``bias=False`` by default to match the (linear, origin-preserving) cross-model maps used in the Procrustes work.
	"""

	def __init__(self, d_a: int, d_b: int, bias: bool = False):
		super().__init__()
		self.proj = nn.Linear(d_a, d_b, bias=bias)

	def forward(self, hidden: torch.Tensor) -> torch.Tensor:
		"""``[batch, seq, d_a] -> [batch, seq, d_b]`` soft embeddings in B's input space."""
		w = self.proj.weight
		return self.proj(hidden.to(dtype=w.dtype, device=w.device))
