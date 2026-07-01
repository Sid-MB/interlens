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
            batched: bool = False, max_batch_size: int | None = None):
	"""Run ``n`` rollouts of a shared scenario across all devices, then optionally analyze each.

	Expands one ``ConversationTemplate`` into ``n`` ``ConversationSpec``s with distinct per-rollout seeds/job ids
	and hands them to ``run_conversations`` (multi-GPU, checkpointed, resumable, failure-isolated). ``analyze``
	runs in-worker while models are resident, so it retains full per-model power — e.g. sample each debater
	"what's your opinion now?" off-transcript, or run a classifier — with only serializable results crossing back.

	With ``batched=True`` (throughput mode) the per-device rollouts are co-stepped: each round's same-position
	turns run in one ``model.generate`` (waves of ``max_batch_size``), and turn 1 — token-identical across
	rollouts — takes the shared-prefill fast path (prefix computed once, forked to all rollouts). This is a
	5-20x throughput win but is **not** token-identical to the default per-rollout path (batch composition +
	global RNG perturb rows; PLAN §Execution modes). Default ``batched=False`` runs each rollout independently.
	"""
	specs = [
		ConversationSpec(template=_rollout_template(template, i, seed), job_id=f"rollout_{i:04d}", turns=turns)
		for i in range(n)
	]
	return run_conversations(specs, devices=devices, analyze=analyze, out_dir=out_dir,
	                         resume=resume, registry=registry, batched=batched, max_batch_size=max_batch_size)
