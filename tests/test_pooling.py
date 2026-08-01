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

# [implement: rational_agents new transformer feature] 2026-08-01 — Agent C.

"""Pure-CPU, pure-torch tests for ``interp/pooling.py``. No model, no tokenizer, no weights.

The activations are a deliberately readable ``hidden[t] = t`` ramp, so every expected pooled value is an
arithmetic mean of integers that the test can state literally rather than recompute with the code under test.
"""
from __future__ import annotations

import pytest
import torch

from interlens.interp import span_pool, group_pool


@pytest.fixture
def ramp() -> torch.Tensor:
	"""``[10, 3]`` where row ``t`` is ``[t, t, t]`` — pooling a span is then just the mean of its indices."""
	return torch.arange(10, dtype=torch.float32).unsqueeze(1).repeat(1, 3)


def test_span_pool_mean_and_last(ramp):
	out = span_pool(ramp, [(0, 4), (4, 5), (7, 10)], mode="mean")
	assert out.shape == (3, 3)
	assert torch.allclose(out[:, 0], torch.tensor([1.5, 4.0, 8.0]))
	out = span_pool(ramp, [(0, 4), (4, 5), (7, 10)], mode="last")
	assert torch.allclose(out[:, 0], torch.tensor([3.0, 4.0, 9.0]))


def test_span_pool_allows_overlap_and_unsorted(ramp):
	out = span_pool(ramp, [(5, 10), (0, 8)], mode="mean")
	assert torch.allclose(out[:, 0], torch.tensor([7.0, 3.5]))


def test_span_pool_empty_span_list_keeps_dtype_and_width(ramp):
	out = span_pool(ramp, [], mode="mean")
	assert out.shape == (0, 3) and out.dtype == ramp.dtype


@pytest.mark.parametrize("spans", [[(4, 4)], [(3, 2)], [(-1, 3)], [(8, 11)]])
def test_span_pool_rejects_empty_or_out_of_bounds(ramp, spans):
	with pytest.raises(ValueError):
		span_pool(ramp, spans)


def test_span_pool_rejects_bad_shape_and_mode(ramp):
	with pytest.raises(ValueError):
		span_pool(ramp.unsqueeze(0), [(0, 2)])
	with pytest.raises(ValueError):
		span_pool(ramp, [(0, 2)], mode="sum")


def test_group_pool_is_token_weighted_not_span_weighted(ramp):
	# One group of a 1-token span and a 4-token span: the mean must be over all 5 tokens (mean of 0,6,7,8,9 =
	# 6.0), NOT the average of the two spans' own means ((0 + 7.5) / 2 = 3.75).
	pooled, valid = group_pool(ramp, [[(0, 1), (6, 10)]], mode="mean")
	assert pooled.shape == (1, 3) and bool(valid[0])
	assert torch.allclose(pooled[0, 0], torch.tensor(6.0))


def test_group_pool_last_takes_highest_ending_span(ramp):
	pooled, _ = group_pool(ramp, [[(6, 9), (0, 2)]], mode="last")
	assert torch.allclose(pooled[0, 0], torch.tensor(8.0))


def test_group_pool_matches_span_pool_on_singleton_groups(ramp):
	spans = [(0, 4), (4, 5), (7, 10)]
	for mode in ("mean", "last"):
		pooled, valid = group_pool(ramp, [[s] for s in spans], mode=mode)
		assert valid.all()
		assert torch.allclose(pooled, span_pool(ramp, spans, mode=mode))


def test_group_pool_empty_group_is_zeros_and_invalid(ramp):
	pooled, valid = group_pool(ramp, [[(0, 2)], [], [(8, 10)]], mode="mean")
	assert valid.tolist() == [True, False, True]
	assert torch.allclose(pooled[1], torch.zeros(3))
	assert torch.allclose(pooled[:, 0], torch.tensor([0.5, 0.0, 8.5]))


def test_group_pool_empty_group_can_raise(ramp):
	with pytest.raises(ValueError):
		group_pool(ramp, [[]], empty="raise")


@pytest.mark.parametrize("fn", ["span", "group"])
def test_pooling_is_autograd_transparent(fn):
	hidden = torch.arange(12, dtype=torch.float32).reshape(6, 2).requires_grad_(True)
	out = span_pool(hidden, [(0, 3)]) if fn == "span" else group_pool(hidden, [[(0, 2), (2, 3)]])[0]
	out.sum().backward()
	# Every one of the three pooled tokens gets an equal 1/3 share of the upstream gradient; nothing else moves.
	assert torch.allclose(hidden.grad[:3], torch.full((3, 2), 1 / 3))
	assert torch.allclose(hidden.grad[3:], torch.zeros(3, 2))
