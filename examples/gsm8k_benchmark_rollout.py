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

This is the end-to-end pattern for "evaluate a *collaborative* protocol on a benchmark":

  1. Load a real benchmark (GSM8K grade-school math word problems) via `datasets`.
  2. Turn EACH problem into one `ConversationSpec` — a short solver/critic dialogue: the solver drafts a
     solution, the critic looks for mistakes, the solver produces the FINAL answer. The problem text is the
     conversation's `shared_context`, so every spec shares the SAME participant schedule but a DIFFERENT question.
     (That is why this uses `run_conversations` over per-problem specs, NOT `rollout` — `rollout` is N copies of
     ONE scenario; a benchmark is N DIFFERENT scenarios.)
  3. Grade each finished conversation in an `analyze` callback (extract the solver's final number, compare to
     gold) — grading runs in-worker while the models are resident, and only the serializable verdict crosses back.
  4. `run_conversations` parallelizes by default on two axes — one worker per GPU, AND batched co-stepping within
     each device (specs are grouped by schedule signature, so all these same-schedule problems batch into one
     `model.generate` per round). No flags needed; that is what makes a real eval tractable.

Run (needs a GPU + `datasets`; the default 1.5B model fits a modest card):

    python examples/gsm8k_benchmark_rollout.py --n 50 --turns 3

Swap in hosted models by editing `build_participants` to return two `APIParticipantConfig`s (set `batch=True`
for the async batch API — anthropic/openai only). See docs/examples/08_rollouts_and_scale.md.
"""
from __future__ import annotations

import argparse
import re

from interlens import ConversationSpec, ModelParticipantConfig, ConversationTemplate, run_conversations

# GSM8K gold answers live after a "#### " marker; predictions end on a final number (possibly comma-grouped).
_GOLD_RE = re.compile(r"####\s*([-\d,]+)")
_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _to_number(text: str) -> str | None:
    """The LAST number in `text`, normalized (commas/trailing .0 stripped) — the convention GSM8K graders use
    since the final line of a worked solution is the answer. Returns None if there is no number."""
    matches = _NUM_RE.findall(text)
    if not matches:
        return None
    n = matches[-1].replace(",", "")
    return n[:-2] if n.endswith(".0") else n


def load_gsm8k(n: int, offset: int) -> list[dict]:
    """A slice of the GSM8K test split as `{qid, question, gold}` dicts (gold = the normalized numeric answer)."""
    from datasets import load_dataset

    ds = load_dataset("openai/gsm8k", "main", split="test")
    rows = ds.select(range(offset, min(offset + n, len(ds))))
    out = []
    for i, r in enumerate(rows):
        gold = _GOLD_RE.search(r["answer"])
        out.append({"qid": f"gsm8k_{offset + i:05d}", "question": r["question"],
                    "gold": gold.group(1).replace(",", "") if gold else None})
    return out


def build_participants(model: str, max_new_tokens: int) -> list[ModelParticipantConfig]:
    """The collaborative protocol: a solver and a critic. Turn order is solver -> critic -> solver, so the LAST
    message is always the solver's final answer. Both roles share one loaded model (same id) — the runner caches
    it once per device. Swap these two configs for `APIParticipantConfig(provider=..., batch=True)` to eval a
    hosted model through its async batch API instead."""
    solver = ModelParticipantConfig(
        name="solver", model=model, max_new_tokens=max_new_tokens, temperature=0.7,
        system_prompt="You solve math word problems. Think step by step, then end with a line "
                      "'Final answer: <number>'.")
    critic = ModelParticipantConfig(
        name="critic", model=model, max_new_tokens=max_new_tokens, temperature=0.7,
        system_prompt="You check the solver's arithmetic and logic. Point out any mistake in one or two "
                      "sentences; if it is correct, say so. Do NOT give the final answer yourself.")
    return [solver, critic]


def make_specs(problems: list[dict], participants: list[ModelParticipantConfig], turns: int) -> list[ConversationSpec]:
    """One spec per problem: same participants + turn count (shared schedule -> batchable), different question."""
    return [
        ConversationSpec(
            template=ConversationTemplate(
                participants=[c.__class__(**vars(c)) for c in participants],  # fresh copies per spec
                shared_context=f"Solve this problem. Show your work and end with 'Final answer: <number>'.\n\n{p['question']}",
                turns=turns),
            job_id=p["qid"], turns=turns)
        for p in problems
    ]


def make_grader(problems: list[dict]):
    """An `analyze(conv)` closure that grades the solver's FINAL turn against gold. Runs in-worker right after the
    conversation finishes; returns a serializable verdict dict. (Closures are fine on a single device — for
    multi-GPU, register a named analyzer instead; see the rollouts doc.)"""
    gold = {p["qid"]: p["gold"] for p in problems}

    def grade(conv) -> dict:
        final = next((m.content for m in reversed(conv.transcript) if m.author == "solver"), "")
        pred = _to_number(final)
        want = gold.get(conv.job_id) if hasattr(conv, "job_id") else None
        return {"pred": pred, "gold": want, "correct": pred is not None and pred == want}

    return grade


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
    ap.add_argument("--out-dir", default=None,
                    help="If set, checkpoint each conversation under this dir (resumable across re-runs).")
    args = ap.parse_args()

    print(f"[gsm8k] invocation: model={args.model} n={args.n} offset={args.offset} turns={args.turns} "
          f"device={args.device} out_dir={args.out_dir}", flush=True)

    problems = load_gsm8k(args.n, args.offset)
    specs = make_specs(problems, build_participants(args.model, args.max_new_tokens), args.turns)
    print(f"[gsm8k] built {len(specs)} per-problem specs; running batched co-stepped eval on {args.device}", flush=True)

    # batched co-stepping + multi-GPU parallelism are ON by default; same-schedule specs batch automatically.
    report = run_conversations(
        specs, devices=[args.device], analyze=make_grader(problems), out_dir=args.out_dir,
        resume=args.out_dir is not None)

    graded = [r.analysis for r in report.results.values() if r.error is None and r.analysis is not None]
    correct = sum(1 for g in graded if g["correct"])
    print(f"\n[gsm8k] accuracy: {correct}/{len(graded)} = {correct / max(1, len(graded)):.1%}")
    if report.failed:
        print(f"[gsm8k] {len(report.failed)} conversations errored: {report.failed[:5]}"
              f"{' …' if len(report.failed) > 5 else ''}")


if __name__ == "__main__":
    main()
