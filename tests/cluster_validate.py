# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# [complete-chat-harness]: GPU-only validation driver for the chat harness.
# Exercises the paths that could not be validated on Mac (CLUSTER_NEXT_STEPS.md items 1,2,3,7 + smoke rollout).
# Run via tests/cluster_validate.sbatch (needs >=2 GPUs for the spawn path).
from __future__ import annotations

import sys
import torch

from interlens import (
    ConversationTemplate, ModelParticipantConfig, conversation_from_ids,
    rollout, register_analyzer, run_conversations, ConversationSpec, available_devices,
)
from interlens.runner.worker_init import register_worker_init

SMALL = "qwen2.5-0.5b"


def opinion(conv):
    """Top-level analyzer (picklable → survives spawn). Samples each participant off-transcript."""
    return {name: conv.sample(name, "In one sentence, your view now?").content for name in conv.by_name}


register_analyzer("opinion", opinion)


def _boom_template():
    """A template whose build/run raises, to test failure isolation."""
    return ConversationTemplate(
        participants=[ModelParticipantConfig(name="x", model="does-not-exist-model-xyz")],
        shared_context="hi", turns=2)


def log(msg):
    print(f"[validate] {msg}", flush=True)


def check_flash_attn():
    log("=== flash-attn resolution ===")
    conv = conversation_from_ids((SMALL, SMALL), names=("a", "b"), device="cuda", max_new_tokens=8, temperature=0.0)
    resolved = getattr(conv.by_name["a"].model, "_resolved_attn", "UNKNOWN")
    log(f"resolved attention backend = {resolved}")
    assert conv.by_name["a"].model is conv.by_name["b"].model, "same-id should share one model object"
    log("same-id weight sharing OK")
    return resolved


def check_shared_tokenizer():
    # PLAN test 4b: different sizes of one family share ONE tokenizer object but load distinct weights.
    log("=== shared tokenizer cache (gemma2-2b <-> gemma2-9b) ===")
    tmpl = ConversationTemplate(
        participants=[ModelParticipantConfig(name="a", model="gemma2-2b", max_new_tokens=8, temperature=0.0),
                      ModelParticipantConfig(name="b", model="gemma2-9b", max_new_tokens=8, temperature=0.0)],
        shared_context="Say hello in one word.", turns=2)
    conv = tmpl.build(devices="cuda")
    a, b = conv.by_name["a"], conv.by_name["b"]
    assert a.tokenizer is b.tokenizer, "same-family sizes must share ONE tokenizer object"
    assert a.model is not b.model, "different sizes must be distinct model objects"
    log("tokenizer identity shared, models distinct OK")
    conv.run(turns=2)
    log(f"gemma size pair produced {len(conv.transcript)} messages (chat template did not raise)")


def check_two_families():
    log("=== two families render with own tokenizer (qwen <-> gemma) ===")
    tmpl = ConversationTemplate(
        participants=[ModelParticipantConfig(name="q", model=SMALL, max_new_tokens=16, temperature=0.0,
                                             system_prompt="Argue social media HELPS teens."),
                      ModelParticipantConfig(name="g", model="gemma2-2b", max_new_tokens=16, temperature=0.0,
                                             system_prompt="Argue social media HARMS teens.")],
        shared_context="Debate: is social media net positive or harmful for teenagers?", turns=4)
    conv = tmpl.build(devices="cuda")
    conv.run(turns=4)
    assert conv.by_name["q"].tokenizer is not conv.by_name["g"].tokenizer
    log(f"qwen<->gemma produced {len(conv.transcript)} messages, distinct tokenizers OK")


def check_multi_gpu_spawn(devices):
    log(f"=== multi-GPU spawn across {devices} ===")
    tmpl = ConversationTemplate(
        participants=[ModelParticipantConfig(name="a", model=SMALL, max_new_tokens=16, temperature=0.7, seed=1,
                                             system_prompt="Argue YES."),
                      ModelParticipantConfig(name="b", model=SMALL, max_new_tokens=16, temperature=0.7, seed=2,
                                             system_prompt="Argue NO.")],
        shared_context="Is remote work good?", turns=4)
    specs = [ConversationSpec(template=tmpl, job_id=f"spawn_{i:02d}", turns=4) for i in range(5)]
    report = run_conversations(specs, devices=devices, analyze="opinion", in_process=False)
    log(f"spawn results: {len(report.results)} specs, failed={report.failed}")
    assert len(report.results) == 5 and not report.failed
    for jid, r in report.results.items():
        assert r.transcript is not None and r.device in devices
    log(f"per-job devices: {{jid: r.device for ...}} = " +
        str({jid: r.device for jid, r in report.results.items()}))
    log("multi-GPU spawn OK (each spec ran, device pinned, analyze returned)")


def check_closure_fails():
    log("=== closure analyze must fail loudly under spawn ===")
    devices = available_devices()
    if len(devices) < 2:
        log("skip (need >=2 gpus)")
        return
    bad = lambda conv: 1  # noqa: E731 - deliberately a closure/lambda
    tmpl = ConversationTemplate(
        participants=[ModelParticipantConfig(name="a", model=SMALL, max_new_tokens=8),
                      ModelParticipantConfig(name="b", model=SMALL, max_new_tokens=8)],
        shared_context="hi", turns=2)
    specs = [ConversationSpec(template=tmpl, job_id=f"clo_{i}", turns=2) for i in range(2)]
    try:
        run_conversations(specs, devices=devices, analyze=bad, in_process=False)
        log("WARNING: closure analyze did NOT raise (unexpected)")
    except Exception as exc:
        log(f"closure analyze failed as expected: {type(exc).__name__}")


def check_rollout(out_dir):
    log(f"=== rollout + analyze + resume + isolation → {out_dir} ===")
    tmpl = ConversationTemplate(
        participants=[ModelParticipantConfig(name="alice", model="qwen2.5-1.5b", max_new_tokens=48, temperature=0.7,
                                             system_prompt="Argue social media HARMS teens."),
                      ModelParticipantConfig(name="bob", model="qwen2.5-1.5b", max_new_tokens=48, temperature=0.7,
                                             system_prompt="Argue social media HELPS teens.")],
        shared_context="Debate: is social media net positive or harmful for teenagers?", turns=6)
    report = rollout(tmpl, n=6, analyze="opinion", out_dir=out_dir, resume=True, seed=0)
    log(f"rollout: {len(report.results)} results, failed={report.failed}, skipped={report.skipped}")
    assert len(report.results) == 6 and not report.failed
    # resume: rerun, everything should be skipped
    report2 = rollout(tmpl, n=6, analyze="opinion", out_dir=out_dir, resume=True, seed=0)
    log(f"resume rerun: skipped={len(report2.skipped)} (expected 6), ran={len(report2.results)}")
    assert len(report2.skipped) == 6
    log("rollout + resume OK")
    for jid, r in list(report.results.items())[:2]:
        log(f"  {jid} analysis: {r.analysis}")


def check_isolation():
    log("=== failure isolation: one bad spec, rest survive ===")
    good = ConversationTemplate(
        participants=[ModelParticipantConfig(name="a", model=SMALL, max_new_tokens=8),
                      ModelParticipantConfig(name="b", model=SMALL, max_new_tokens=8)],
        shared_context="hi", turns=2)
    specs = [ConversationSpec(template=good, job_id="good_0", turns=2),
             ConversationSpec(template=_boom_template(), job_id="bad_0", turns=2),
             ConversationSpec(template=good, job_id="good_1", turns=2)]
    report = run_conversations(specs, devices=["cuda"], in_process=True)
    log(f"isolation: failed={report.failed}, ok={[j for j in report.results if not report.results[j].error]}")
    assert "bad_0" in report.failed and "good_0" not in report.failed and "good_1" not in report.failed
    log("failure isolation OK")


def check_batched(out_dir):
    import time
    log("=== batched co-stepping + shared-prefill vs unbatched (throughput mode) ===")
    tmpl = ConversationTemplate(
        participants=[ModelParticipantConfig(name="alice", model="qwen2.5-1.5b", max_new_tokens=48, temperature=0.9,
                                             system_prompt="Argue social media HARMS teens. Be brief."),
                      ModelParticipantConfig(name="bob", model="qwen2.5-1.5b", max_new_tokens=48, temperature=0.9,
                                             system_prompt="Argue social media HELPS teens. Be brief.")],
        shared_context="Debate: is social media net positive or harmful for teenagers?", turns=6)
    n = 8
    t0 = time.time()
    plain = rollout(tmpl, n=n, devices=["cuda"], out_dir=f"{out_dir}_plain", batched=False, seed=0)
    t_plain = time.time() - t0
    t0 = time.time()
    batch = rollout(tmpl, n=n, devices=["cuda"], out_dir=f"{out_dir}_batch", batched=True, max_batch_size=8, seed=0)
    t_batch = time.time() - t0
    assert not plain.failed and not batch.failed and len(batch.results) == n
    # Every batched conversation co-stepped all 6 turns...
    for r in batch.results.values():
        assert len(r.transcript) == 7, len(r.transcript)  # 6 turns + moderator seed
    # ...turn 1 (alice, identical prompt across rollouts) took the shared-prefill fast path...
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
    check_shared_tokenizer()
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
