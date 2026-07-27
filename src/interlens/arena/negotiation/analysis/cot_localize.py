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

# [rational_agents restructure: phase-C] 2026-07-24 — moved up from experiments/rational_agents/analysis/:
# negotiation-generic measurement, reusable by any experiment over this game family.
"""OmegaPRM-style within-CoT divergence localization: binary-search the first reasoning step that flips the
induced action to a divergent one, in O(log n) oracle calls (arXiv:2406.06592 — exploit prefix monotonicity:
correct until the first error, wrong after). Re-deriving an action from a truncated CoT is the LLM hook
(``induced_action_hook``); the search skeleton here is model-agnostic and tested against a synthetic oracle.
"""
from __future__ import annotations

import re
from typing import Callable


def split_steps(scratchpad: str) -> list[str]:
	"""Split a CoT scratchpad into reasoning steps. Default heuristic: numbered/bulleted lines ("1.", "-",
	"Step 3:") start new steps, otherwise blank-line-separated paragraphs, otherwise single newlines. A scenario
	that emits already-structured steps should pass them in directly rather than re-splitting."""
	text = (scratchpad or "").strip()
	if not text:
		return []
	# numbered or bulleted markers at line starts
	markers = list(re.finditer(r"(?m)^\s*(?:\d+[.)]|[-*•]|[Ss]tep\s+\d+[:.)])\s+", text))
	if len(markers) >= 2:
		bounds = [m.start() for m in markers] + [len(text)]
		return [text[bounds[i]:bounds[i + 1]].strip() for i in range(len(bounds) - 1)]
	paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
	if len(paras) >= 2:
		return paras
	return [ln.strip() for ln in text.splitlines() if ln.strip()]


def localize_first_divergence(n_steps: int, is_divergent: Callable[[int], bool]) -> int | None:
	"""Binary-search the earliest prefix length ``j`` (1..n_steps) whose induced action is divergent.

	``is_divergent(j)`` reports whether the action induced by the first ``j`` steps diverges from the oracle;
	it is assumed monotone (non-divergent for short prefixes, divergent once the erroneous step is included),
	which is the OmegaPRM prefix-correctness assumption. Returns the first divergent step index (1-based), or
	``None`` if even the full CoT does not induce a divergent action. Makes O(log n_steps) calls to
	``is_divergent`` — each call is one (expensive) re-derivation + oracle check in production."""
	if n_steps <= 0:
		return None
	if not is_divergent(n_steps):
		return None            # the full reasoning induces a non-divergent action
	lo, hi = 1, n_steps
	while lo < hi:
		mid = (lo + hi) // 2
		if is_divergent(mid):
			hi = mid
		else:
			lo = mid + 1
	return lo


def induced_action_hook(prefix_steps: list[str]):
	"""HOOK (unimplemented): re-derive the action a truncated CoT induces by force-continuing the model from the
	joined ``prefix_steps``; wrap with the oracle's divergence check to form ``is_divergent`` for
	``localize_first_divergence``. Model generation is out of the metrics layer's scope."""
	raise NotImplementedError(
		"induced_action_hook needs a model re-derivation (force-continue from the CoT prefix); supply your own "
		"is_divergent to localize_first_divergence — see annotate.py and the synthetic tests")
