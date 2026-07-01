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

import torch


def token_logprobs(scores: tuple[torch.Tensor, ...], generated_ids: torch.Tensor) -> dict:
	"""Compute per-token logprobs / surprisal / entropy for a generation.

	``scores`` is the tuple of per-step logit tensors from ``model.generate(..., output_scores=True,
	return_dict_in_generate=True)`` (one ``[vocab]`` per generated token); ``generated_ids`` are the sampled
	token ids. Returns lists suitable to drop into ``Message.metadata`` — scalar-per-token, so they stay small
	and don't violate the "no heavy tensors in metadata" invariant.

	Surprisal = -logprob (nats); entropy is the full next-token distribution entropy at each step (a readout of
	the model's uncertainty, distinct from the surprisal of the token it actually emitted).
	"""
	if len(scores) == 0:
		return {"logprobs": [], "surprisal": [], "entropy": []}
	# Stack once -> [steps, vocab]; batch all ops so there is a single GPU->CPU sync at the end.
	logits = torch.stack([s[0] for s in scores]).float()
	logp = torch.log_softmax(logits, dim=-1)
	toks = torch.as_tensor(generated_ids, device=logp.device, dtype=torch.long)[: logp.shape[0]]
	lp = logp.gather(1, toks.unsqueeze(1)).squeeze(1)
	ent = -(logp.exp() * logp).sum(dim=-1)
	logprobs = lp.tolist()
	return {
		"logprobs": logprobs,
		"surprisal": (-lp).tolist(),
		"entropy": ent.tolist(),
	}
