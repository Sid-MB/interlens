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
