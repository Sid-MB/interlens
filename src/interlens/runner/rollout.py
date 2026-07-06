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

from ..template import ConversationTemplate
from .spec import ConversationSpec
from .pool import run_conversations


def _rollout_template(template: ConversationTemplate, index: int, seed: int | None) -> ConversationTemplate:
	"""Deep-copy the template (via its dict form) and give each model participant a distinct per-rollout seed, so
	sampled rollouts diverge but remain reproducible. Greedy (temperature 0) rollouts are identical by design."""
	clone = ConversationTemplate.from_dict(template.to_dict())
	if seed is not None:
		for cfg in clone.participants:
			if hasattr(cfg, "seed"):
				cfg.seed = seed + index
	return clone


def rollout(template: ConversationTemplate, n: int, turns: int | None = None, devices=None,
            analyze=None, seed: int = 0, resume: bool = False, out_dir=None, registry=None,
            batched: bool = True, max_batch_size: int | None = None):
	"""Run ``n`` rollouts of a shared scenario across all devices, then optionally analyze each.

	Expands one ``ConversationTemplate`` into ``n`` ``ConversationSpec``s with distinct per-rollout seeds/job ids
	and hands them to ``run_conversations`` (multi-GPU, checkpointed, resumable, failure-isolated). ``analyze``
	runs in-worker while models are resident, so it retains full per-model power — e.g. sample each debater
	"what's your opinion now?" off-transcript, or run a classifier — with only serializable results crossing back.

	**Throughput is on by default** (``batched=True``): a rollout is ``n`` clones of one template, so every round's
	same-position turns share a schedule and are co-stepped — local ``ModelParticipant``s always run in one
	``model.generate`` (waves of ``max_batch_size``; turn 1, token-identical across rollouts, takes the
	shared-prefill fast path), and ``batch=True`` API participants go through their provider's async batch API.
	This is a 5-20x throughput win. Local batching is unconditional here — there is no per-model opt-out (see
	``batched.co_step`` / ``_batchable``).

	``batched=False`` is the ``ExecutionMode.DETERMINISTIC`` escape hatch: it runs each rollout independently and
	is **token-identical** on the same hardware, at the cost of throughput. Use it only when you need exact replay
	or per-turn interp (capture/steering/probes), which batched generation cannot provide; the default throughput
	path guarantees only *distributional* reproducibility (batch composition + global RNG perturb rows).
	"""
	specs = [
		ConversationSpec(template=_rollout_template(template, i, seed), job_id=f"rollout_{i:04d}", turns=turns)
		for i in range(n)
	]
	return run_conversations(specs, devices=devices, analyze=analyze, out_dir=out_dir,
	                         resume=resume, registry=registry, batched=batched, max_batch_size=max_batch_size)
