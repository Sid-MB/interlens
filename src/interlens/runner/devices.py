from __future__ import annotations

import torch


def available_devices() -> list[str]:
	"""List the devices to spread conversations across: every CUDA GPU, else a single mps/cpu fallback.

	Multi-GPU parallelism lives *across* conversations (they're independent); within one conversation turns are
	sequential, so more GPUs never speed up a single conversation — only throughput over many."""
	if torch.cuda.is_available():
		return [f"cuda:{i}" for i in range(torch.cuda.device_count())]
	if torch.backends.mps.is_available():
		return ["mps"]
	return ["cpu"]
