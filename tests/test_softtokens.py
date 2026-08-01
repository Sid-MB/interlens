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

"""Fast CPU tests for ``interp/softtokens.py`` — virtual-token injection and span-pooled residual reads.

No pretrained weights: a *randomly initialized* tiny Qwen2 (3 layers, d_model=64) in float32 on CPU is enough,
since every assertion is about plumbing (which positions get which embeddings, whether grads flow, tensor shapes)
rather than about what the model says. Only the real tokenizer is loaded, for its vocabulary and chat template —
those are exactly what the placeholder round-trip has to survive.
"""
from __future__ import annotations

import pytest
import torch

from interlens.interp import VirtualTokenInjector, span_pooled_residuals, forward_with_grad, GradCaptureSpec

TOKENIZER_ID = "Qwen/Qwen2.5-0.5B-Instruct"  # tokenizer only; weights are never downloaded


@pytest.fixture(scope="module")
def tokenizer():
	from transformers import AutoTokenizer
	try:
		return AutoTokenizer.from_pretrained(TOKENIZER_ID)
	except Exception as exc:  # no cache and no network -> nothing to test against
		pytest.skip(f"tokenizer {TOKENIZER_ID} unavailable: {exc}")


@pytest.fixture(scope="module")
def model(tokenizer):
	from transformers import Qwen2Config, Qwen2ForCausalLM
	torch.manual_seed(0)
	cfg = Qwen2Config(vocab_size=max(tokenizer.get_vocab().values()) + 1, hidden_size=64, intermediate_size=128,
	                  num_hidden_layers=3, num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=512,
	                  tie_word_embeddings=True)
	m = Qwen2ForCausalLM(cfg).to(torch.float32).eval()
	return m


@pytest.fixture(scope="module")
def injector(tokenizer):
	return VirtualTokenInjector(tokenizer, n_soft=4)


def _ids(tokenizer, text: str) -> torch.Tensor:
	return tokenizer(text, add_special_tokens=False, return_tensors="pt").input_ids


# -- placeholder selection ---------------------------------------------------------------------------------------

def test_placeholder_round_trips_through_chat_template(tokenizer, injector):
	"""The snippet survives ``apply_chat_template`` as exactly ``n_soft`` contiguous copies of one id."""
	rendered = tokenizer.apply_chat_template(
		[{"role": "system", "content": "sys"}, {"role": "user", "content": f"look: {injector.text} ok"}],
		tokenize=False, add_generation_prompt=True)
	assert injector.text in rendered
	ids = tokenizer(rendered, add_special_tokens=False).input_ids
	assert ids.count(injector.token_id) == injector.n_soft
	start = ids.index(injector.token_id)
	assert ids[start:start + injector.n_soft] == [injector.token_id] * injector.n_soft


def test_placeholder_is_an_existing_vocab_token(tokenizer, injector):
	"""No vocabulary surgery: the placeholder is already in the tokenizer, so no embedding resize is implied."""
	assert injector.placeholder in tokenizer.get_vocab()
	assert injector.token_id < len(tokenizer.get_vocab())
	assert len(_ids(tokenizer, injector.text)[0]) == injector.n_soft


def test_bad_placeholder_is_rejected(tokenizer):
	with pytest.raises(ValueError):
		VirtualTokenInjector(tokenizer, n_soft=3, placeholder="the")  # multi-use word token: run is not unique
	with pytest.raises(ValueError):
		VirtualTokenInjector(tokenizer, n_soft=0)


def test_run_starts_locates_and_validates(tokenizer, injector, model):
	ids = _ids(tokenizer, f"hello {injector.text} world")
	(start,) = injector.run_starts(ids)
	assert ids[0, start:start + injector.n_soft].tolist() == [injector.token_id] * injector.n_soft
	partial = ids.clone()
	partial[0, start] = 0  # break the run -> partial match must raise rather than steer the wrong positions
	with pytest.raises(ValueError):
		injector.run_starts(partial)


# -- injection ---------------------------------------------------------------------------------------------------

def test_injection_matches_manual_inputs_embeds_splice(tokenizer, injector, model):
	"""Forward with the injector == forward on ``inputs_embeds`` with the same vectors spliced in by hand."""
	ids = _ids(tokenizer, f"a {injector.text} b")
	(start,) = injector.run_starts(ids)
	d = model.config.hidden_size
	torch.manual_seed(1)
	vectors = torch.randn(1, injector.n_soft, d)

	with injector.inject(model, vectors):
		hooked = forward_with_grad(model, input_ids=ids).logits

	embeds = model.get_input_embeddings()(ids).clone()
	embeds[0, start:start + injector.n_soft] = vectors[0]
	manual = forward_with_grad(model, inputs_embeds=embeds).logits

	assert torch.allclose(hooked, manual, atol=1e-5), (hooked - manual).abs().max().item()


def test_injection_actually_changes_the_forward(tokenizer, injector, model):
	"""Sanity: the substitution is not a no-op — different vectors give different logits."""
	ids = _ids(tokenizer, f"a {injector.text} b")
	d = model.config.hidden_size
	base = forward_with_grad(model, input_ids=ids).logits
	with injector.inject(model, torch.full((1, injector.n_soft, d), 3.0)):
		steered = forward_with_grad(model, input_ids=ids).logits
	assert not torch.allclose(base, steered, atol=1e-3)


def test_hooks_are_removed_on_exit_and_on_error(tokenizer, injector, model):
	ids = _ids(tokenizer, f"a {injector.text} b")
	d = model.config.hidden_size
	base = forward_with_grad(model, input_ids=ids).logits
	with pytest.raises(RuntimeError):
		with injector.inject(model, torch.zeros(1, injector.n_soft, d)):
			raise RuntimeError("boom")
	after = forward_with_grad(model, input_ids=ids).logits
	assert torch.allclose(base, after)


def test_gradients_flow_into_the_vectors(tokenizer, injector, model):
	"""The whole point of the design: a loss on the model backpropagates into the injected vectors."""
	ids = _ids(tokenizer, f"a {injector.text} b")
	d = model.config.hidden_size
	vectors = torch.zeros(1, injector.n_soft, d, requires_grad=True)
	with injector.inject(model, vectors):
		logits = forward_with_grad(model, input_ids=ids).logits
	logits.float().log_softmax(-1)[0, -1, 100].backward()
	assert vectors.grad is not None
	assert torch.isfinite(vectors.grad).all()
	assert vectors.grad.abs().sum() > 0


def test_gradients_flow_through_a_linear_bridge(tokenizer, injector, model):
	"""End-to-end shape the ToM head will use: bridge params get gradient from the listener's loss."""
	from interlens.interp import LinearBridge
	ids = _ids(tokenizer, f"a {injector.text} b")
	d = model.config.hidden_size
	bridge = LinearBridge(d_a=8, d_b=d)
	vectors = bridge(torch.ones(1, injector.n_soft, 8))
	with injector.inject(model, vectors):
		logits = forward_with_grad(model, input_ids=ids).logits
	logits.float().sum().backward()
	assert bridge.proj.weight.grad is not None and bridge.proj.weight.grad.abs().sum() > 0


def test_batched_mixed_rows(tokenizer, injector, model):
	"""A batch where only some rows carry placeholders: those rows change, the others are bit-identical."""
	tokenizer.padding_side = "left"
	with_ph = f"a {injector.text} b"
	without = "a plain sentence with no placeholders at all"
	enc = tokenizer([with_ph, without], add_special_tokens=False, return_tensors="pt", padding=True)
	ids, mask = enc.input_ids, enc.attention_mask
	d = model.config.hidden_size

	base = forward_with_grad(model, input_ids=ids, attention_mask=mask).logits
	torch.manual_seed(2)
	vectors = torch.randn(2, injector.n_soft, d)
	with injector.inject(model, vectors):
		out = forward_with_grad(model, input_ids=ids, attention_mask=mask).logits

	assert not torch.allclose(base[0], out[0], atol=1e-3)   # row 0 has placeholders -> changed
	assert torch.allclose(base[1], out[1], atol=1e-6)       # row 1 has none -> untouched


def test_generate_smoke_with_left_padding(tokenizer, injector, model):
	"""Injection survives ``model.generate`` (prefill sees the placeholders, cached decode steps do not)."""
	tokenizer.padding_side = "left"
	enc = tokenizer([f"a {injector.text} b", "another prompt here"], add_special_tokens=False,
	                return_tensors="pt", padding=True)
	d = model.config.hidden_size
	with injector.inject(model, torch.zeros(2, injector.n_soft, d)):
		out = model.generate(input_ids=enc.input_ids, attention_mask=enc.attention_mask, max_new_tokens=3,
		                     do_sample=False, pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id)
	assert out.shape == (2, enc.input_ids.shape[1] + 3)


# -- span-pooled residual reads ----------------------------------------------------------------------------------

@pytest.fixture
def view():
	return [{"role": "user", "content": "what is your offer"},
	        {"role": "assistant", "content": "three apples for two pears"}]


def test_span_pooled_shapes_and_layers(model, tokenizer, view):
	pooled = span_pooled_residuals(model, tokenizer, view, layers=(0, -1))
	n_layers = model.config.num_hidden_layers
	assert set(pooled) == {("residual", 0), ("residual", n_layers - 1)}
	for tensor in pooled.values():
		assert tensor.shape == (len(view), model.config.hidden_size)


def test_span_pooled_mean_and_last_match_manual_pooling(model, tokenizer, view):
	"""Values, not just shapes: pooling matches hand-pooled ``hidden_states`` over the same message spans."""
	from interlens.interp import message_token_spans
	spans = message_token_spans(tokenizer, view)
	ids = tokenizer(tokenizer.apply_chat_template(view, tokenize=False), add_special_tokens=False,
	                return_tensors="pt").input_ids
	with torch.inference_mode():
		hs = model(ids, output_hidden_states=True, use_cache=False).hidden_states[-1][0]  # last layer, [seq, d]

	mean = span_pooled_residuals(model, tokenizer, view, layers=-1, pool="mean")[("residual", model.config.num_hidden_layers - 1)]
	last = span_pooled_residuals(model, tokenizer, view, layers=-1, pool="last")[("residual", model.config.num_hidden_layers - 1)]
	for i, (s, e) in enumerate(spans):
		assert torch.allclose(mean[i], hs[s:e].mean(0), atol=1e-5)
		assert torch.allclose(last[i], hs[e - 1], atol=1e-5)


def test_span_pooled_grad_variant_is_connected(model, tokenizer, view):
	"""``grad=True`` keeps the pooled vectors in the autograd graph (the detached variant does not)."""
	detached = span_pooled_residuals(model, tokenizer, view, layers=-1, grad=False)[("residual", model.config.num_hidden_layers - 1)]
	assert detached.grad_fn is None
	live = span_pooled_residuals(model, tokenizer, view, layers=-1, grad=True)[("residual", model.config.num_hidden_layers - 1)]
	assert live.requires_grad and live.grad_fn is not None
	live.sum().backward()
	assert model.get_input_embeddings().weight.grad is not None


def test_span_pooled_rejects_unknown_pool(model, tokenizer, view):
	with pytest.raises(ValueError):
		span_pooled_residuals(model, tokenizer, view, layers=-1, pool="max")
