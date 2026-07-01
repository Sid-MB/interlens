from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import torch

Site = Literal["residual", "attn", "mlp"]
Phase = Literal["prompt", "reasoning", "answer"]
OffloadLocation = Literal["cpu"] | None  # where captured tensors live: "cpu" = move off-GPU as recorded; None = keep on-device


def offload_to_cpu(tensors: list[torch.Tensor]) -> list[torch.Tensor]:
	"""Move a list of GPU tensors to CPU efficiently, preserving order.

	Two wins over per-tensor ``.to('cpu')``: (1) **batching** — same-shape/dtype tensors are stacked into one D2H
	copy, so N transfer launches collapse to one per shape-group; (2) **pinned + non_blocking** — the copy goes
	through a pinned host staging buffer, which hits full PCIe bandwidth (pageable D2H is throttled by CUDA's
	internal bounce buffer) and lets the transfer overlap with compute. Results are cloned into pageable memory so
	the (limited) pinned buffer is freed immediately rather than pinned for the cache's lifetime. Falls back to a
	plain detach/copy when there's nothing to gain (CPU inputs or CUDA unavailable)."""
	if not tensors:
		return []
	if not tensors[0].is_cuda:
		return [t.detach() for t in tensors]
	# Group by (shape, dtype), preserving first-seen order, so each group is a single stacked transfer.
	groups: dict[tuple, list[int]] = {}
	for i, t in enumerate(tensors):
		groups.setdefault((tuple(t.shape), t.dtype), []).append(i)
	out: list[torch.Tensor | None] = [None] * len(tensors)
	for (_shape, dtype), idxs in groups.items():
		stacked = torch.stack([tensors[i].detach() for i in idxs])
		host = torch.empty(stacked.shape, dtype=dtype, device="cpu").pin_memory()
		host.copy_(stacked, non_blocking=True)
		torch.cuda.synchronize()  # ensure the async D2H completed before we read the buffer
		for j, i in enumerate(idxs):
			out[i] = host[j].clone()  # clone into pageable memory; frees the pinned buffer at loop end
	return out  # type: ignore[return-value]


@dataclass
class CaptureSpec:
	"""What to capture during a generation: which ``sites`` at which ``layers``, and where to keep the tensors.

	Capture defaults to a *narrow* set — you pass the layers/sites you actually want — because capturing all
	layers × all tokens × many rollouts OOMs fast. ``offload='cpu'`` moves captured tensors off-GPU as they are
	recorded (essential for large sweeps); ``offload=None`` keeps them on-device.
	"""

	sites: tuple[Site, ...] = ("residual",)
	layers: tuple[int, ...] | None = None  # None = all layers
	offload: OffloadLocation = "cpu"


@dataclass
class ActivationRecord:
	"""One captured tensor plus everything needed to know *what it is*.

	``tensor`` is ``[seq, d_model]`` for one (participant turn, layer, site). ``phases`` maps ``prompt`` /
	``reasoning`` / ``answer`` to ``(start, end)`` token indices into that sequence, so reasoning-vs-answer
	activations are separable for CoT models. ``token_span`` is the ``(prompt_len, seq_len)`` boundary between
	the fed-in prompt and the newly generated tokens.
	"""

	participant: str
	message_idx: int
	layer: int
	site: Site
	tensor: torch.Tensor
	token_span: tuple[int, int]
	phases: dict[Phase, tuple[int, int]] = field(default_factory=dict)


class ActivationCache:
	"""A queryable store of captured activations, tagged by conversation structure.

	Records know which participant/turn/layer/site they came from, so a downstream probe can ask for "bob's turn
	3, layer 18, the answer span" rather than juggling anonymous tensors. This is the object every interp
	consumer reads; the harness never puts activations in ``Message.metadata`` (that would blow up ``branch()``'s
	transcript copy), so the cache is the single home for heavy tensors.
	"""

	def __init__(self, offload: OffloadLocation = "cpu"):
		self.offload = offload
		self.records: list[ActivationRecord] = []

	def add(self, record: ActivationRecord) -> None:
		if self.offload == "cpu":
			record.tensor = record.tensor.detach().to("cpu")
		else:
			record.tensor = record.tensor.detach()
		self.records.append(record)

	def add_batch(self, records: list[ActivationRecord]) -> None:
		"""Add many records at once, offloading all their tensors in one batched pinned transfer (see
		``offload_to_cpu``). Preferred over a loop of ``add`` when a single capture pass produces many records —
		it turns N GPU->CPU copies into one per shape-group."""
		if not records:
			return
		if self.offload == "cpu":
			offloaded = offload_to_cpu([r.tensor for r in records])
			for r, t in zip(records, offloaded):
				r.tensor = t
		else:
			for r in records:
				r.tensor = r.tensor.detach()
		self.records.extend(records)

	def query(self, *, participant=None, message_idx=None, layer=None, site=None) -> list[ActivationRecord]:
		def ok(r):
			return (
				(participant is None or r.participant == participant)
				and (message_idx is None or r.message_idx == message_idx)
				and (layer is None or r.layer == layer)
				and (site is None or r.site == site)
			)
		return [r for r in self.records if ok(r)]

	def at(self, *, participant=None, message_idx=None, layer=None, site="residual") -> torch.Tensor:
		"""Return the single matching tensor, erroring if the filters aren't unique — the ergonomic accessor for
		"give me exactly this activation"."""
		matches = self.query(participant=participant, message_idx=message_idx, layer=layer, site=site)
		if len(matches) != 1:
			raise KeyError(f"expected exactly one record, got {len(matches)} for "
			               f"participant={participant} message_idx={message_idx} layer={layer} site={site}")
		return matches[0].tensor

	def __len__(self) -> int:
		return len(self.records)

	def __iter__(self):
		return iter(self.records)
