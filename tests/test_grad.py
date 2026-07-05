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

"""Real-model tests for the gradient / soft-embedding path (opt-in). Run with:

    uv run pytest tests/test_grad.py -m slow

Loads a small Qwen in float32 (so the one-hot equivalence check is tight) on cuda if present, else cpu. Covers:
soft_embed one-hot equivalence, grad flow into a soft prompt, two-model grad flow (A logits -> gumbel -> soft_embed
-> B logp -> grads reach A), and checkpoint==no-checkpoint equivalence of loss and gradients.
"""
from __future__ import annotations

import pytest
import torch

pytestmark = pytest.mark.slow

MODEL_A = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_B = "Qwen/Qwen2.5-0.5B-Instruct"  # same id -> shared weights, enough to exercise the A->B plumbing


@pytest.fixture(scope="module")
def device():
	return "cuda" if torch.cuda.is_available() else "cpu"


@pytest.fixture(scope="module")
def model_b(device):
	from interlens.loading import load_model
	model, tok = load_model(MODEL_B, device=device, dtype=torch.float32, attn="eager")
	return model, tok


def test_soft_embed_one_hot_equivalence(model_b, device):
	from interlens import soft_embed
	model, tok = model_b
	ids = tok("The capital of France is", return_tensors="pt").input_ids.to(device)
	vocab = model.get_input_embeddings().weight.shape[0]
	one_hot = torch.zeros(*ids.shape, vocab, device=device)
	one_hot.scatter_(2, ids.unsqueeze(2), 1.0)
	soft = soft_embed(model, one_hot)
	hard = model.get_input_embeddings()(ids)
	assert torch.allclose(soft, hard, atol=1e-4), (soft - hard).abs().max().item()


def test_soft_prompt_grad_flow(model_b, device):
	from interlens import continuation_logprob
	model, tok = model_b
	d_model = model.get_input_embeddings().weight.shape[1]
	soft_prompt = torch.zeros(1, 4, d_model, device=device, requires_grad=True)
	target = tok(" Paris", return_tensors="pt", add_special_tokens=False).input_ids.to(device)
	logp = continuation_logprob(model, prefix_embeds=soft_prompt, target_ids=target)
	logp.backward()
	assert soft_prompt.grad is not None
	assert torch.isfinite(soft_prompt.grad).all()
	assert soft_prompt.grad.abs().sum() > 0


def test_two_model_grad_flow(model_b, device):
	"""A's logits -> gumbel_softmax -> soft_embed(B) -> B logp -> grads reach A's params."""
	from interlens.loading import load_model
	from interlens import soft_embed, gumbel_softmax_tokens, continuation_logprob
	model_a, tok = load_model(MODEL_A, device=device, dtype=torch.float32, attn="eager")
	# A produces logits over a short prompt; take the last position's next-token distribution for k soft tokens.
	prompt = tok("Say a fruit:", return_tensors="pt").input_ids.to(device)
	a_out = model_a(input_ids=prompt)
	last_logits = a_out.logits[:, -1:, :]  # [1, 1, V]
	k = 3
	soft_logits = last_logits.expand(1, k, -1)
	probs = gumbel_softmax_tokens(soft_logits, tau=1.0, hard=False)
	prefix_embeds = soft_embed(model_b[0], probs)
	target = tok(" apple", return_tensors="pt", add_special_tokens=False).input_ids.to(device)
	loss = -continuation_logprob(model_b[0], prefix_embeds=prefix_embeds, target_ids=target)
	loss.backward()
	grads = [p.grad for p in model_a.parameters() if p.grad is not None]
	assert grads, "no gradient reached model A"
	assert any(g.abs().sum() > 0 for g in grads)


def test_checkpoint_matches_no_checkpoint(model_b, device):
	from interlens import continuation_logprob
	model, tok = model_b
	d_model = model.get_input_embeddings().weight.shape[1]
	target = tok(" Paris", return_tensors="pt", add_special_tokens=False).input_ids.to(device)

	def run(checkpoint):
		sp = torch.full((1, 4, d_model), 0.01, device=device, requires_grad=True)
		logp = continuation_logprob(model, prefix_embeds=sp, target_ids=target, checkpoint=checkpoint)
		logp.backward()
		return logp.detach(), sp.grad.detach()

	l0, g0 = run(False)
	l1, g1 = run(True)
	assert torch.allclose(l0, l1, atol=1e-4)
	assert torch.allclose(g0, g1, atol=1e-4), (g0 - g1).abs().max().item()
