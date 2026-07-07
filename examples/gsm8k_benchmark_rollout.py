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

"""Run a two-model **conversation rollout over a real evaluation benchmark** (GSM8K) and report accuracy.

The whole pattern is one lazy ``Conversation`` recipe expanded over a HuggingFace ``Dataset`` — no templates, no
specs, no configs, and **no materializing the data into Python lists** (so it scales to datasets far larger than
memory):

  1. Load GSM8K as a ``Dataset`` and add a normalized ``gold`` column with a lazy ``.map`` (Arrow-backed on disk;
     the same code works with ``streaming=True``, i.e. an ``IterableDataset``, for a 100-TB corpus).
  2. Build ONE solver/critic ``Conversation`` whose ``shared_context`` is templated with ``dataset_field`` so each
     dataset row becomes a different question — then ``.data(ds).analyzer(grade).rollout()``.
  3. ``rollout`` **streams** the dataset one row at a time, making an independent COPY of the conversation per row
     (the original is never mutated). The source row is stashed on ``conv.row``, so the ``analyzer`` grades the
     solver's final answer against ``conv.row["gold"]`` — per-row gold reaches grading WITHOUT leaking into the
     model's view. Finished conversations come back on ``report.results[id]``.
  4. Parallel by default on two axes — one worker per GPU AND batched co-stepping within each device (same-schedule
     rows batch into one ``model.generate`` per round). No flags needed.

Run (needs a GPU + ``datasets``; the default 1.5B model fits a modest card):

    python examples/gsm8k_benchmark_rollout.py --n 50 --turns 3
    python examples/gsm8k_benchmark_rollout.py --n 50 --streaming     # same, via a streaming IterableDataset

Swap in hosted models by editing ``build_conversation`` to use ``APIParticipant``s (set ``batch=True`` for the
async batch API — anthropic/openai only). See docs/examples/08_rollouts_and_scale.md.
"""
from __future__ import annotations

import argparse
import re

from interlens import Conversation, AutoModelParticipant, dataset_field

# GSM8K gold answers live after a "#### " marker; predictions end on a final number (possibly comma-grouped).
_GOLD_RE = re.compile(r"####\s*([-\d,]+)")
_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _to_number(text: str) -> str | None:
	"""The LAST number in ``text``, normalized (commas/trailing .0 stripped) — the convention GSM8K graders use,
	since the final line of a worked solution is the answer. Returns None if there is no number."""
	matches = _NUM_RE.findall(text)
	if not matches:
		return None
	n = matches[-1].replace(",", "")
	return n[:-2] if n.endswith(".0") else n


def _normalize_gold(row: dict) -> dict:
	"""Map fn adding a normalized numeric ``gold`` column parsed from GSM8K's ``#### <answer>`` marker."""
	m = _GOLD_RE.search(row["answer"])
	return {"gold": m.group(1).replace(",", "") if m else None}


def load_gsm8k(n: int, offset: int, streaming: bool):
	"""GSM8K's test split as a HuggingFace ``Dataset`` (or streaming ``IterableDataset``) with a ``gold`` column
	added lazily via ``.map`` — **never converted to a list**, so it stays memory-flat regardless of size."""
	from datasets import load_dataset

	ds = load_dataset("openai/gsm8k", "main", split="test", streaming=streaming)
	ds = ds.skip(offset).take(n) if streaming else ds.select(range(offset, min(offset + n, len(ds))))
	return ds.map(_normalize_gold)


def build_conversation(model: str, max_new_tokens: int, turns: int, dataset) -> Conversation:
	"""The collaborative protocol as ONE data-parameterized recipe: a solver and a critic sharing one lazily-loaded
	model (same id → cached once per device), with the problem templated into ``shared_context`` via
	``dataset_field`` so every row is a different question. Turn order solver → critic → solver, so the LAST message
	is always the solver's final answer. Swap the two participants for ``APIParticipant``s to eval a hosted model."""
	solver = AutoModelParticipant.from_pretrained(
		model, name="solver", max_new_tokens=max_new_tokens, temperature=0.7,
		system_prompt="You solve math word problems. Think step by step, then end with a line "
		              "'Final answer: <number>'.")
	critic = AutoModelParticipant.from_pretrained(
		model, name="critic", max_new_tokens=max_new_tokens, temperature=0.7,
		system_prompt="You check the solver's arithmetic and logic. Point out any mistake in one or two "
		              "sentences; if it is correct, say so. Do NOT give the final answer yourself.")
	return (Conversation(
	            participants=[solver, critic],
	            shared_context=("Solve this problem. Show your work and end with 'Final answer: <number>'.\n\n",
	                            dataset_field("question")))       # templated per row (a constructor field)
	        .turns(turns)                                          # rollout/data fields use dot-modifier sugar
	        .data(dataset)                                         # a Dataset / IterableDataset — streamed, not listed
	        .analyzer(grade))


def grade(conv) -> dict:
	"""Analyzer: grade the solver's FINAL turn against the row's gold, read from ``conv.row`` (the dataset row that
	produced this conversation) — no side dict, no substring matching. Runs in-worker right after the conversation
	finishes and returns a serializable verdict. (Fine as a top-level function for the single-device path; it is
	also importable-by-name, so it survives the multi-GPU spawn boundary.)"""
	final = next((m.content for m in reversed(conv.transcript) if m.author == "solver"), "")
	pred = _to_number(final)
	want = conv.row.get("gold")
	return {"pred": pred, "gold": want, "correct": pred is not None and pred == want}


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct",
	                help="HF model id for BOTH roles (loaded once per device). A small instruct model keeps the "
	                     "example cheap; scale up for real numbers.")
	ap.add_argument("--n", type=int, default=50, help="How many benchmark problems to evaluate.")
	ap.add_argument("--offset", type=int, default=0, help="Start index into the GSM8K test split (for sharding).")
	ap.add_argument("--turns", type=int, default=3,
	                help="Conversation length. 3 = solver -> critic -> solver (the last turn is the final answer).")
	ap.add_argument("--device", default="cuda", help="Device to run on (e.g. 'cuda', 'cuda:0', 'cpu').")
	ap.add_argument("--max-new-tokens", type=int, default=512, help="Per-turn generation cap.")
	ap.add_argument("--streaming", action="store_true",
	                help="Load the benchmark as a streaming IterableDataset (rows pulled on demand) instead of a "
	                     "map-style Dataset — the memory-flat path for corpora too large to fit on disk/RAM.")
	ap.add_argument("--out-dir", default=None,
	                help="If set, checkpoint each conversation under this dir (resumable across re-runs).")
	args = ap.parse_args()

	print(f"[gsm8k] invocation: model={args.model} n={args.n} offset={args.offset} turns={args.turns} "
	      f"device={args.device} streaming={args.streaming} out_dir={args.out_dir}", flush=True)

	dataset = load_gsm8k(args.n, args.offset, args.streaming)
	conv = build_conversation(args.model, args.max_new_tokens, args.turns, dataset)
	print(f"[gsm8k] built recipe; streaming rollout (batched co-step) on {args.device}", flush=True)

	# batched co-stepping + multi-GPU parallelism are ON by default; same-schedule rows batch automatically.
	report = conv.rollout(devices=[args.device], out_dir=args.out_dir, resume=args.out_dir is not None)

	graded = [r.analysis for r in report.results.values() if r.error is None and r.analysis is not None]
	correct = sum(1 for g in graded if g["correct"])
	print(f"\n[gsm8k] accuracy: {correct}/{len(graded)} = {correct / max(1, len(graded)):.1%}")
	if report.failed:
		print(f"[gsm8k] {len(report.failed)} conversations errored: {report.failed[:5]}"
		      f"{' …' if len(report.failed) > 5 else ''}")


if __name__ == "__main__":
	main()
