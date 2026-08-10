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

"""Where to put a model's *inputs*, which is not the same question as "what device is the model on".

A single-device model answers both with one device, so ``model.device`` and ``next(model.parameters()).device``
are interchangeable and every call site historically used whichever was shorter. A model sharded across GPUs by
``device_map=`` answers them differently: its parameters live on several devices, and ``input_ids`` must land on
whichever one holds the **input embedding**, because that is the first module the tensor meets. Accelerate's
hooks move activations *between* shards for you, but they do not move the tensor you hand to ``forward``.

Hence :func:`input_device` — one helper, used by every site that places `input_ids`, so single-device behavior
is bit-identical to before and sharded behavior is correct.
"""

from __future__ import annotations

import torch


def device_map_kind(device) -> str | dict | None:
	"""Interpret a ``device`` argument as a ``device_map`` when it names a sharding strategy, else ``None``.

	Accepts the strings transformers understands (``"auto"``, ``"balanced"``, ``"balanced_low_0"``,
	``"sequential"``) and an explicit ``{module: device}`` dict. Anything else — ``"cuda"``, ``"cuda:1"``,
	``"cpu"``, a ``torch.device`` — is an ordinary single-device placement and returns ``None``, which is what
	keeps the default load path unchanged.
	"""
	if isinstance(device, dict):
		return device
	if isinstance(device, str) and device in ("auto", "balanced", "balanced_low_0", "sequential"):
		return device
	return None


def is_sharded(model) -> bool:
	"""True if ``model`` was placed by ``device_map=`` across more than one device (including cpu/disk offload).

	Reads accelerate's ``hf_device_map``, which ``from_pretrained(device_map=...)`` stamps on the model. A
	single-entry map (everything on one device) reads as NOT sharded, because in that case ``model.device`` is
	already the right answer everywhere.
	"""
	device_map = getattr(model, "hf_device_map", None)
	return bool(device_map) and len({str(d) for d in device_map.values()}) > 1


def input_device(model) -> torch.device:
	"""The device to place ``input_ids`` on for ``model``: its input embedding's device.

	Resolution order, each step falling through on failure so this never raises on an exotic model:

	1. ``model.get_input_embeddings()``'s first parameter/buffer — correct under any ``device_map``, and equal
	   to the model's single device when there is no sharding.
	2. ``model.device`` — the historical answer, kept for models that expose no input embedding (mocks, some
	   wrappers).
	3. the first parameter's device.

	Returns a ``torch.device`` (never a string), so callers can compare and ``.to()`` it directly.
	"""
	try:
		embed = model.get_input_embeddings()
	except Exception:
		embed = None
	if embed is not None:
		for tensor in list(embed.parameters()) + list(embed.buffers()):
			return tensor.device
	device = getattr(model, "device", None)
	if device is not None:
		return torch.device(device) if not isinstance(device, torch.device) else device
	for tensor in model.parameters():
		return tensor.device
	raise ValueError(f"cannot resolve an input device for {type(model).__name__}: it has no input embedding, "
	                 f"no .device, and no parameters")
