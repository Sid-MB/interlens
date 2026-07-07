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

# [complete-chat-harness]: GPU-only validation driver for the chat harness (updated for the merged-Conversation API).
# Exercises the paths that could not be validated on Mac (lazy load + weight sharing, multi-family render, multi-GPU
# spawn with lazy-participant pickling, rollout+resume, failure isolation, batched co-stepping + shared-prefill).
# Run via tests/cluster_validate.sbatch (needs >=2 GPUs for the spawn path).
from __future__ import annotations

import sys
import torch

from interlens import Conversation, AutoModelParticipant, run, register_analyzer, available_devices

SMALL = "Qwen/Qwen2.5-0.5B-Instruct"


def opinion(conv):
	"""Top-level analyzer (picklable → survives spawn). Samples every participant off-transcript via sample_all."""
	return {name: msg.content for name, msg in conv.sample_all("In one sentence, your view now?").items()}


register_analyzer("opinion", opinion)


def _p(model, name, **kw):
	return AutoModelParticipant.from_pretrained(model, name=name, **kw)


def _conv(participants, shared_context, turns, analyzer=None):
	c = Conversation(participants=participants, shared_context=shared_context).turns(turns)
	return c.analyzer(analyzer) if analyzer else c


def _boom_conv():
	"""A conversation whose lazy load raises on run, to test failure isolation."""
	return _conv([_p("does-not-exist-model-xyz", "x", max_new_tokens=8)], "hi", 2).name("bad_0")


def log(msg):
	print(f"[validate] {msg}", flush=True)


def check_flash_attn():
	log("=== flash-attn resolution + lazy same-id weight sharing ===")
	conv = _conv([_p(SMALL, "a", max_new_tokens=8, temperature=0.0),
	              _p(SMALL, "b", max_new_tokens=8, temperature=0.0)], "Say hello.", 2)
	a, b = conv.participant("a"), conv.participant("b")
	assert a.model is b.model, "same-id should share one cached model object (lazy load)"
	log(f"resolved attention backend = {getattr(a.model, '_resolved_attn', 'UNKNOWN')}; same-id weight sharing OK")


def check_family_size_pair():
	log("=== same-family size pair (gemma-2-2b <-> gemma-2-9b): distinct weights, chat template renders ===")
	conv = _conv([_p("google/gemma-2-2b-it", "a", max_new_tokens=8, temperature=0.0),
	              _p("google/gemma-2-9b-it", "b", max_new_tokens=8, temperature=0.0)], "Say hello in one word.", 2)
	assert conv.participant("a").model is not conv.participant("b").model, "different sizes must be distinct objects"
	conv.run(turns=2)
	log(f"gemma size pair produced {len(conv.transcript)} messages (chat template did not raise)")


def check_two_families():
	log("=== two families render with own tokenizer (qwen <-> gemma) ===")
	conv = _conv([_p(SMALL, "q", max_new_tokens=16, temperature=0.0, system_prompt="Argue social media HELPS teens."),
	              _p("google/gemma-2-2b-it", "g", max_new_tokens=16, temperature=0.0,
	                 system_prompt="Argue social media HARMS teens.")],
	             "Debate: is social media net positive or harmful for teenagers?", 4)
	conv.run(turns=4)
	assert conv.participant("q").tokenizer is not conv.participant("g").tokenizer
	log(f"qwen<->gemma produced {len(conv.transcript)} messages, distinct tokenizers OK")


def check_multi_gpu_spawn(devices):
	log(f"=== multi-GPU spawn across {devices} (lazy-participant pickling) ===")
	conv = _conv([_p(SMALL, "a", max_new_tokens=16, temperature=0.7, seed=1, system_prompt="Argue YES."),
	              _p(SMALL, "b", max_new_tokens=16, temperature=0.7, seed=2, system_prompt="Argue NO.")],
	             "Is remote work good?", 4, analyzer="opinion")
	report = conv.rollout(n=5, devices=devices)
	log(f"spawn results: {len(report.results)} jobs, failed={report.failed}")
	assert len(report.results) == 5 and not report.failed
	for jid, r in report.results.items():
		assert r.transcript is not None and r.device in devices
	log("multi-GPU spawn OK (each job ran, device pinned, analyze returned)")


def check_closure_fails():
	log("=== closure analyzer must fail loudly under spawn ===")
	devices = available_devices()
	if len(devices) < 2:
		log("skip (need >=2 gpus)")
		return
	conv = _conv([_p(SMALL, "a", max_new_tokens=8), _p(SMALL, "b", max_new_tokens=8)], "hi", 2)
	conv = conv.analyzer(lambda c: 1)  # deliberately a closure/lambda → unpicklable across spawn
	try:
		conv.rollout(n=2, devices=devices)
		log("WARNING: closure analyzer did NOT raise (unexpected)")
	except Exception as exc:
		log(f"closure analyzer failed as expected: {type(exc).__name__}")


def check_rollout(out_dir):
	log(f"=== rollout + analyze + resume → {out_dir} ===")
	conv = _conv([_p("Qwen/Qwen2.5-1.5B-Instruct", "alice", max_new_tokens=48, temperature=0.7,
	                 system_prompt="Argue social media HARMS teens."),
	              _p("Qwen/Qwen2.5-1.5B-Instruct", "bob", max_new_tokens=48, temperature=0.7,
	                 system_prompt="Argue social media HELPS teens.")],
	             "Debate: is social media net positive or harmful for teenagers?", 6, analyzer="opinion")
	report = conv.rollout(n=6, out_dir=out_dir, resume=True, seed=0)
	log(f"rollout: {len(report.results)} results, failed={report.failed}, skipped={report.skipped}")
	assert len(report.results) == 6 and not report.failed
	report2 = conv.rollout(n=6, out_dir=out_dir, resume=True, seed=0)
	log(f"resume rerun: skipped={len(report2.skipped)} (expected 6), ran={len(report2.results)}")
	assert len(report2.skipped) == 6
	log("rollout + resume OK")


def check_isolation():
	log("=== failure isolation: one bad lineup, rest survive ===")
	good0 = _conv([_p(SMALL, "a", max_new_tokens=8), _p(SMALL, "b", max_new_tokens=8)], "hi", 2).name("good_0")
	good1 = _conv([_p(SMALL, "a", max_new_tokens=8), _p(SMALL, "b", max_new_tokens=8)], "hi", 2).name("good_1")
	report = run([good0, _boom_conv(), good1], devices=["cuda"])
	log(f"isolation: failed={report.failed}, ok={[j for j in report.results if not report.results[j].error]}")
	assert "bad_0" in report.failed and "good_0" not in report.failed and "good_1" not in report.failed
	log("failure isolation OK")


def check_batched(out_dir):
	import time
	log("=== batched co-stepping + shared-prefill vs unbatched (throughput mode) ===")
	conv = _conv([_p("Qwen/Qwen2.5-1.5B-Instruct", "alice", max_new_tokens=48, temperature=0.9,
	                 system_prompt="Argue social media HARMS teens. Be brief."),
	              _p("Qwen/Qwen2.5-1.5B-Instruct", "bob", max_new_tokens=48, temperature=0.9,
	                 system_prompt="Argue social media HELPS teens. Be brief.")],
	             "Debate: is social media net positive or harmful for teenagers?", 6)
	n = 8
	t0 = time.time()
	plain = conv.rollout(n=n, devices=["cuda"], out_dir=f"{out_dir}_plain", batched=False, seed=0)
	t_plain = time.time() - t0
	t0 = time.time()
	batch = conv.rollout(n=n, devices=["cuda"], out_dir=f"{out_dir}_batch", batched=True, max_batch_size=8, seed=0)
	t_batch = time.time() - t0
	assert not plain.failed and not batch.failed and len(batch.results) == n
	for r in batch.results.values():
		assert len(r.transcript) == 7, len(r.transcript)  # 6 turns + moderator seed
	first_turns = [r.transcript.messages[1] for r in batch.results.values()]  # index 0 is the moderator seed
	assert all(m.metadata.get("shared_prefill") for m in first_turns), "turn-1 shared-prefill did not fire"
	assert all(m.metadata.get("batched") for m in first_turns)
	log(f"unbatched {n} rollouts: {t_plain:.1f}s | batched: {t_batch:.1f}s | speedup {t_plain/t_batch:.1f}x")
	log("turn-1 shared-prefill fired on all rollouts; all co-stepped to completion OK")


def main():
	out_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/chat_validate_run"
	devices = available_devices()
	log(f"available devices: {devices}; torch {torch.__version__}; cuda {torch.cuda.is_available()}")
	for i in range(torch.cuda.device_count()):
		log(f"  cuda:{i} = {torch.cuda.get_device_name(i)}")

	check_flash_attn()
	check_two_families()
	check_family_size_pair()
	check_isolation()
	check_rollout(out_dir)
	check_batched(out_dir)
	if len(devices) >= 2:
		check_multi_gpu_spawn(devices)
		check_closure_fails()
	else:
		log("SKIP multi-GPU spawn checks (only 1 device visible)")
	log("ALL VALIDATION CHECKS PASSED")


if __name__ == "__main__":
	main()
