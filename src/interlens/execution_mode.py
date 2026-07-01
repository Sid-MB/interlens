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

from enum import Enum


class ExecutionMode(str, Enum):
	"""Names the deterministic-vs-throughput tension explicitly rather than pretending it doesn't exist.

	Token-identical replay, performant defaults (flash-attn + KV reuse + batched generation), and interp
	measurement fidelity are NOT jointly satisfiable on CUDA, so callers pick a mode:

	- ``DETERMINISTIC``: batching off, KV reuse off, sdpa/eager attention, deterministic algorithms. Slower, but
	  token-identical on the same hardware and safe for capture/steering/probes. Backs the identical-replay
	  guarantee.
	- ``THROUGHPUT`` (default for large rollouts): flash-attn + batched generation + KV reuse. Guarantees only
	  *distributional* reproducibility.

	P1 defines the switch and threads it through; the optimizations it gates (batching, KV reuse) land in later
	phases and consult this flag.
	"""

	DETERMINISTIC = "deterministic"
	THROUGHPUT = "throughput"
