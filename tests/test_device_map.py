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

# [rational_agents: port-32b] 2026-08-09 — session eb951d8f (port-32b lane).

"""The multi-GPU load surface: ``device_map`` routing, ``max_memory``, and input placement under sharding.

Two things are being pinned here, and the second is the one that actually bites. The first is that a *sharding*
``device`` (``"auto"`` and friends, or an explicit map) reaches ``from_pretrained`` as ``device_map=`` and
suppresses the ``.to(device)`` that would undo it, while every ordinary placement behaves exactly as before —
this is the "additive, default-unchanged" claim, tested rather than asserted. The second is that once a model
IS sharded, ``model.device`` and ``next(model.parameters()).device`` are no longer the device inputs belong on;
only the input embedding's device is, and every site that places ``input_ids`` must agree on that.

No weights are downloaded: ``from_pretrained`` is monkeypatched to a recorder, and the sharding cases use a tiny
hand-built module whose embedding deliberately sits on a *different* device from the rest of it (both on cpu, so
this runs anywhere — the test is about which module is asked, not about CUDA).
"""
from __future__ import annotations

import pytest
import torch

from interlens.loading import devices, load, model_cache


# --- device_map_kind: which strings mean "shard me" ---------------------------------------------------------

@pytest.mark.parametrize("value", ["auto", "balanced", "balanced_low_0", "sequential"])
def test_strategy_strings_are_device_maps(value):
	assert devices.device_map_kind(value) == value


@pytest.mark.parametrize("value", ["cuda", "cuda:1", "cpu", "mps", torch.device("cpu"), None])
def test_ordinary_placements_are_not_device_maps(value):
	assert devices.device_map_kind(value) is None


def test_explicit_dict_is_a_device_map():
	explicit = {"model.embed_tokens": 0, "model.layers.0": 1}
	assert devices.device_map_kind(explicit) == explicit


# --- input_device / is_sharded ------------------------------------------------------------------------------

class _Split(torch.nn.Module):
	"""A stand-in for a sharded model: the embedding is on ``embed_device`` and everything else elsewhere.

	``hf_device_map`` mimics what ``from_pretrained(device_map=...)`` stamps on the model, and ``.device``
	deliberately reports the NON-embedding device — the exact trap the helper exists to avoid.
	"""

	def __init__(self, embed_device="cpu", other_device="cpu", sharded=True):
		super().__init__()
		self.embed = torch.nn.Embedding(4, 2).to(embed_device)
		self.head = torch.nn.Linear(2, 4).to(other_device)
		# The MAP's labels are what ``is_sharded`` reads, and accelerate writes real GPU ordinals there. They are
		# kept independent of where the tensors actually sit so this runs on a CPU-only box.
		self.hf_device_map = {"embed": 0, "head": 1} if sharded else {"": 0}
		self._reported = other_device

	@property
	def device(self):
		return torch.device(self._reported)

	def get_input_embeddings(self):
		return self.embed


def test_input_device_reads_the_embedding_not_the_reported_device():
	model = _Split()
	assert devices.input_device(model) == next(model.embed.parameters()).device


def test_is_sharded_distinguishes_a_multi_device_map_from_a_single_entry_one():
	assert devices.is_sharded(_Split(sharded=True))
	assert not devices.is_sharded(_Split(sharded=False))
	assert not devices.is_sharded(torch.nn.Linear(2, 2))  # no hf_device_map at all


def test_input_device_falls_back_to_dot_device_when_there_is_no_embedding():
	class NoEmbed(torch.nn.Module):
		device = torch.device("cpu")

		def get_input_embeddings(self):
			raise NotImplementedError

	assert devices.input_device(NoEmbed()) == torch.device("cpu")


def test_input_device_falls_back_to_the_first_parameter():
	linear = torch.nn.Linear(2, 2)
	assert devices.input_device(linear) == next(linear.parameters()).device


# --- load_model: what actually reaches from_pretrained ------------------------------------------------------

@pytest.fixture
def recorder(monkeypatch):
	"""Replace weight loading + tokenizer loading with recorders, and clear the process cache around the test."""
	calls: list[dict] = []

	class FakeModel(torch.nn.Module):
		def __init__(self, **kwargs):
			super().__init__()
			self.embed = torch.nn.Embedding(2, 2)
			self.moved_to = None

		def eval(self):
			return self

		def to(self, device):            # records that the historical .to() path fired
			self.moved_to = device
			return self

		def get_input_embeddings(self):
			return self.embed

	def fake_from_pretrained(hf_id, **kwargs):
		calls.append({"hf_id": hf_id, **kwargs})
		return FakeModel()

	class FakeAuto:
		from_pretrained = staticmethod(fake_from_pretrained)

	monkeypatch.setattr(load, "_auto_model_class", lambda hf_id, revision: FakeAuto)
	monkeypatch.setattr(load, "load_tokenizer", lambda hf_id, revision=None: object())
	model_cache.free()
	yield calls
	model_cache.free()


def test_default_load_is_unchanged_no_device_map_and_a_real_to(recorder):
	model, _ = load.load_model("tiny/model")
	assert "device_map" not in recorder[0] and "max_memory" not in recorder[0]
	assert model.moved_to == "cuda"


def test_auto_routes_to_device_map_and_skips_the_move(recorder):
	model, _ = load.load_model("tiny/model", device="auto")
	assert recorder[0]["device_map"] == "auto"
	assert model.moved_to is None, "a sharded model must never be .to()'d — it would undo the placement"


def test_max_memory_is_forwarded(recorder):
	budget = {0: "70GiB", 1: "70GiB", "cpu": "0GiB"}
	load.load_model("tiny/model", device="balanced", max_memory=budget)
	assert recorder[0]["max_memory"] == budget


def test_max_memory_is_ignored_without_a_strategy(recorder):
	load.load_model("tiny/model", device="cuda:0")
	assert "max_memory" not in recorder[0]


# --- the weight-cache key must see the new options ----------------------------------------------------------

def test_device_map_and_single_device_do_not_share_a_cache_slot(recorder):
	a, _ = load.load_model("tiny/model", device="cuda")
	b, _ = load.load_model("tiny/model", device="auto")
	assert a is not b and len(recorder) == 2


def test_different_max_memory_budgets_do_not_share_a_cache_slot(recorder):
	a, _ = load.load_model("tiny/model", device="auto", max_memory={0: "70GiB"})
	b, _ = load.load_model("tiny/model", device="auto", max_memory={0: "40GiB"})
	assert a is not b and len(recorder) == 2


def test_the_same_budget_in_a_different_key_order_shares_one_model(recorder):
	a, _ = load.load_model("tiny/model", device="auto", max_memory={0: "70GiB", 1: "70GiB"})
	b, _ = load.load_model("tiny/model", device="auto", max_memory={1: "70GiB", 0: "70GiB"})
	assert a is b and len(recorder) == 1, "dict order must not split the cache — it would load 62GB twice"


def test_an_explicit_device_map_dict_is_a_usable_cache_key(recorder):
	explicit = {"model.embed_tokens": 0, "model.layers.0": 1}
	a, _ = load.load_model("tiny/model", device=explicit)
	b, _ = load.load_model("tiny/model", device=dict(reversed(list(explicit.items()))))
	assert a is b and len(recorder) == 1


# --- the participant places inputs on the embedding shard ---------------------------------------------------

def test_participant_input_device_follows_the_embedding_under_sharding():
	from interlens import ModelParticipant

	participant = ModelParticipant(name="p", device="cuda:7")   # a label that is deliberately WRONG for inputs
	participant._model = _Split()
	participant._tokenizer = object()
	assert participant.input_device == next(participant._model.embed.parameters()).device
	assert str(participant.device) == "cuda:7", "the identity/cache label must be left alone"
