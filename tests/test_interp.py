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

"""Interp pieces testable without model weights: ActivationCache tagging/query, steering summary, logprobs."""
from __future__ import annotations

import pytest
import torch

from interlens.interp.activation_cache import ActivationCache, ActivationRecord
from interlens import SteeringSpec, token_logprobs


def _record(participant="alice", turn=0, layer=8, site="residual", seq=5, d=16):
	return ActivationRecord(participant=participant, message_idx=turn, layer=layer, site=site,
	                        tensor=torch.randn(seq, d), token_span=(2, seq), phases={"answer": (2, seq)})


def test_cache_add_query_and_offload():
	cache = ActivationCache(offload="cpu")
	cache.add(_record(layer=4))
	cache.add(_record(layer=8))
	assert len(cache) == 2
	assert {r.layer for r in cache.query(participant="alice")} == {4, 8}
	assert cache.query(layer=4)[0].tensor.device.type == "cpu"


def test_cache_at_requires_unique():
	cache = ActivationCache(offload=None)
	cache.add(_record(layer=8))
	t = cache.at(participant="alice", layer=8, site="residual")
	assert t.shape[1] == 16
	cache.add(_record(layer=8))  # now ambiguous
	with pytest.raises(KeyError):
		cache.at(participant="alice", layer=8, site="residual")


def test_steering_summary_records_spec():
	spec = SteeringSpec(direction=torch.ones(16), layers=(6,), coef=3.0, mode="ablate")
	s = spec.summary()
	assert s["mode"] == "ablate" and s["layers"] == [6] and s["coef"] == 3.0
	assert s["direction_norm"] == pytest.approx(4.0)  # ||ones(16)|| = 4


def test_token_logprobs_shapes_and_signs():
	vocab = 32
	scores = [torch.randn(1, vocab) for _ in range(4)]
	gen = torch.tensor([3, 7, 1, 0])
	out = token_logprobs(scores, gen)
	assert len(out["logprobs"]) == len(out["surprisal"]) == len(out["entropy"]) == 4
	assert all(s >= 0 for s in out["surprisal"])   # surprisal = -logprob >= 0
	assert all(e >= 0 for e in out["entropy"])


def test_decoder_layers_unwraps_peft():
	"""decoder_layers must see through a PEFT/adapter wrapper (exposes get_base_model) to the real layer stack —
	otherwise grad/capture on a LoRA-wrapped attacker raises (regression: multimodel-backprop rungs 3/4)."""
	import torch.nn as nn
	from interlens import decoder_layers

	class _Base(nn.Module):
		def __init__(self):
			super().__init__()
			self.model = nn.Module()
			self.model.layers = nn.ModuleList([nn.Linear(4, 4) for _ in range(3)])

	class _PeftLike(nn.Module):
		def __init__(self, base):
			super().__init__()
			self._base = base
		def get_base_model(self):
			return self._base

	base = _Base()
	assert len(decoder_layers(base)) == 3
	assert len(decoder_layers(_PeftLike(base))) == 3


# --- MoE routing (weights-free: synthetic RoutingCapture) ---------------------------------------

def _routing_caps(n_layers=2, n_experts=6, k=2, seq=5, seed=0):
	from interlens.interp.routing import RoutingCapture
	g = torch.Generator().manual_seed(seed)
	caps = []
	for l in range(n_layers):
		logits = torch.randn(seq, n_experts, generator=g)
		probs = torch.softmax(logits, dim=-1)
		tp, ti = probs.topk(k, dim=-1)
		caps.append(RoutingCapture(layer=l, router_logits=logits,
		                           topk_experts=ti.to(torch.int16), topk_probs=tp.to(torch.float16)))
	return caps


def test_routing_stats_histogram_normalized_and_span_selected():
	from interlens.interp import routing_stats
	caps = _routing_caps(n_layers=2, n_experts=6, seq=5)
	st = routing_stats(caps, n_experts=6, spans=[(1, 4)])
	assert st.expert_load.shape == (2, 6)
	# each layer's load is a distribution over experts (top-k selections normalized) -> rows sum to 1
	assert torch.allclose(st.expert_load.sum(-1), torch.ones(2), atol=1e-5)
	assert st.n_tokens == 3 and st.top_k == 2
	assert st.expert_mass is not None and st.expert_mass.shape == (2, 6)


def test_routing_stats_rejects_empty_span():
	from interlens.interp import routing_stats
	with pytest.raises(ValueError):
		routing_stats(_routing_caps(seq=5), n_experts=6, spans=[(3, 3)])


def test_routing_divergences_self_zero_and_overlap_full():
	from interlens.interp import routing_stats, kl_divergence, js_divergence, topk_expert_overlap
	p = routing_stats(_routing_caps(seed=1), n_experts=6).expert_load
	q = routing_stats(_routing_caps(seed=2), n_experts=6).expert_load
	assert kl_divergence(p, p).abs().max() < 1e-5      # KL(p||p)=0
	assert js_divergence(p, p).abs().max() < 1e-5      # JS(p||p)=0
	assert (js_divergence(p, q) >= -1e-6).all()        # JS >= 0
	assert (topk_expert_overlap(p, p, k=2) >= 1.0 - 1e-6).all()  # a dist fully overlaps itself
