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
