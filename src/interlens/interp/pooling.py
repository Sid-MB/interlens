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

# [implement: rational_agents new transformer feature] 2026-08-01 — Agent C.

"""Pool a token-position axis down to one vector per span — the primitive under every span-level readout.

``span_pooled_residuals`` pools one span per *message*; a theory-of-mind probe instead pools one vector per
*speaker* (many disjoint, non-contiguous spans per group) out of a single long forward pass, and a probe over
prefix-shared conversation turns pools many overlapping span sets out of that same pass. Both want the same
arithmetic, so it lives here once, as plain tensor math with no model, tokenizer, or conversation in sight.

Two entry points:

- :func:`span_pool` — one vector per ``(start, end)`` span, contiguous, the ``span_pooled_residuals`` shape.
- :func:`group_pool` — one vector per *group of spans*, for "everything this speaker said" reads where a group's
  spans are scattered through the sequence. ``mean`` is taken over the group's pooled tokens (token-weighted, so
  a long message counts more than a short one), ``last`` takes the final token of the group's last span.

Both are autograd-transparent (no ``detach``, no in-place writes into the input), so they compose with
``forward_with_grad`` when the pooled vectors feed a trainable head.
"""

from __future__ import annotations

from typing import Literal, Sequence

import torch

Pool = Literal["mean", "last"]
Span = tuple[int, int]


def _check_span(start: int, end: int, seq: int) -> None:
	if not (0 <= start < end <= seq):
		raise ValueError(f"span {(start, end)} is empty or out of bounds for a {seq}-token sequence")


def span_pool(hidden: torch.Tensor, spans: Sequence[Span], mode: Pool = "mean") -> torch.Tensor:
	"""Pool ``hidden[start:end]`` for each span; returns ``[len(spans), d_model]``.

	Args:
		hidden: ``[seq, d_model]`` per-token activations from one forward pass (any site, any layer).
		spans: half-open ``(start, end)`` token ranges. Spans may overlap and need not be sorted, but each must
			be non-empty and within ``seq`` — an empty span is a bug in the span construction, not a zero vector,
			so it raises rather than silently contributing nothing.
		mode: ``"mean"`` averages the span's tokens (order-insensitive; the probe default) while ``"last"`` takes
			the span's final token (the position that causally sees the whole span, and what a next-token readout
			actually conditions on).

	Raises:
		ValueError: on a non-2D ``hidden``, an unknown ``mode``, or an empty/out-of-bounds span.
	"""
	if hidden.dim() != 2:
		raise ValueError(f"expected [seq, d_model] hidden, got shape {tuple(hidden.shape)}")
	if mode not in ("mean", "last"):
		raise ValueError(f"unknown pool mode {mode!r}; expected 'mean' or 'last'")
	if len(spans) == 0:
		return hidden.new_zeros((0, hidden.shape[1]))
	seq = hidden.shape[0]
	rows = []
	for start, end in spans:
		_check_span(start, end, seq)
		rows.append(hidden[start:end].mean(0) if mode == "mean" else hidden[end - 1])
	return torch.stack(rows)


def group_pool(hidden: torch.Tensor, groups: Sequence[Sequence[Span]], mode: Pool = "mean",
               empty: Literal["zeros", "raise"] = "zeros") -> tuple[torch.Tensor, torch.Tensor]:
	"""Pool each *group* of spans into one vector; returns ``([len(groups), d_model], valid[len(groups)])``.

	The multi-span generalization of :func:`span_pool`: a group is an arbitrary set of (possibly scattered,
	possibly overlapping) token ranges — e.g. every message one speaker contributed to a long transcript. Under
	``"mean"`` the average is over the union of the group's *token positions*, taken with multiplicity if spans
	overlap, so a speaker's long message weighs more than a short one; under ``"last"`` the result is the final
	token of the group's highest-ending span.

	Args:
		hidden: ``[seq, d_model]`` per-token activations.
		groups: one span list per output row. Groups are what varies across a batch of readouts sharing one
			forward pass, which is why they are the outer axis.
		mode: as in :func:`span_pool`.
		empty: what an *empty group* means. ``"zeros"`` (default) emits a zero row and marks it invalid in the
			returned mask — the right behaviour when a group is legitimately absent (a party that has not spoken
			yet at this point in the dialogue), so callers can mask it downstream instead of dropping the row and
			losing alignment. ``"raise"`` treats it as a construction bug.

	Returns:
		``(pooled, valid)`` where ``pooled`` is ``[len(groups), d_model]`` and ``valid`` is a bool tensor that is
		``False`` exactly on rows pooled from an empty group. Always check ``valid`` before using a row: a zero
		row is indistinguishable from a genuine zero activation without it.
	"""
	if hidden.dim() != 2:
		raise ValueError(f"expected [seq, d_model] hidden, got shape {tuple(hidden.shape)}")
	if mode not in ("mean", "last"):
		raise ValueError(f"unknown pool mode {mode!r}; expected 'mean' or 'last'")
	if empty not in ("zeros", "raise"):
		raise ValueError(f"unknown empty policy {empty!r}; expected 'zeros' or 'raise'")
	seq = hidden.shape[0]
	rows, valid = [], []
	for gi, spans in enumerate(groups):
		if len(spans) == 0:
			if empty == "raise":
				raise ValueError(f"group {gi} has no spans")
			rows.append(hidden.new_zeros(hidden.shape[1]))
			valid.append(False)
			continue
		for start, end in spans:
			_check_span(start, end, seq)
		if mode == "last":
			rows.append(hidden[max(end for _, end in spans) - 1])
		else:
			total = sum(end - start for start, end in spans)
			acc = sum(hidden[start:end].sum(0) for start, end in spans)
			rows.append(acc / total)
		valid.append(True)
	return torch.stack(rows), torch.tensor(valid, dtype=torch.bool)
