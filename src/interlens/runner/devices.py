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


def available_devices() -> list[str]:
	"""List the devices to spread conversations across: every CUDA GPU, else a single mps/cpu fallback.

	Multi-GPU parallelism lives *across* conversations (they're independent); within one conversation turns are
	sequential, so more GPUs never speed up a single conversation — only throughput over many."""
	if torch.cuda.is_available():
		return [f"cuda:{i}" for i in range(torch.cuda.device_count())]
	if torch.backends.mps.is_available():
		return ["mps"]
	return ["cpu"]
