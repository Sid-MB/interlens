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

# [complete-chat-harness]: co-stepping batched runner (PLAN item 5 / CLUSTER_NEXT_STEPS item 5).
# Steps a group of independent conversations that SHARE participant/model objects in lockstep, batching each
# round's same-position turns into ONE model.generate — the biggest rollout throughput win. Throughput mode
# only: batch composition + the global RNG perturb rows, so tokens are NOT identical to unbatched (PLAN
# §Execution modes). Conversations that can't batch (tools, non-ModelParticipant speaker) fall back to the
# per-conversation .step within the same round, so a mixed group still runs correctly.
from __future__ import annotations

from ..participant.participants.model_participant import ModelParticipant


def _participant_signature(p):
	"""A key identifying what a participant would batch AS. Two participants share a key only when co-stepping
	them in one batch is correct: local models must be the SAME cached weight object (``id(p.model)`` — the model
	cache keys on hf_id/device/dtype/…, so same-id participants share the object); API participants must hit the
	same provider+model+batch mode; anything else (tools/human/non-batch API) is per-conv so keyed by role."""
	if isinstance(p, ModelParticipant):
		return ("model", id(getattr(p, "model", None)))
	if type(p).__name__ == "APIParticipant":
		return ("api", getattr(p, "provider", None), getattr(p, "model_id", None), bool(getattr(p, "batch", False)))
	return ("other", type(p).__name__, getattr(p, "name", None))


def schedule_signature(conv, turns: int):
	"""The full co-step schedule of a conversation: its turn count + the per-position participant signatures. Convs
	that share a signature have an identical speaker/model schedule, so ``co_step`` can batch each round's
	same-position turns across them safely. Grouping specs by this (instead of by turn count alone) makes batched
	execution correct for ANY mix of specs — a heterogeneous lineup simply forms its own group."""
	return (int(turns), tuple(_participant_signature(p) for p in conv.participants))


def _chunks(items, size):
	if not size or size <= 0 or size >= len(items):
		return [items]
	return [items[i:i + size] for i in range(0, len(items), size)]


def _batchable(participant) -> bool:
	# ANY local ModelParticipant (base or any family subclass — qwen/gemma/llama/…) always batches locally: they
	# all inherit ``generate_batch``, so the check is capability-based (isinstance), never a per-family allowlist a
	# new family could silently fall out of. An APIParticipant batches only with batch=True (its provider async
	# batch API). Tool loops take the per-conv path regardless (the batched path has no tools loop).
	if getattr(participant, "tools", ()):
		return False
	if isinstance(participant, ModelParticipant):
		return True
	return type(participant).__name__ == "APIParticipant" and getattr(participant, "batch", False)


def co_step(convs, turns: int, *, max_batch_size: int | None = None, group_seed: int = 0):
	"""Co-step ``convs`` (all built from the same template, so a shared turn schedule) for ``turns`` rounds.

	Each round: every conversation's current speaker is the same schedule position, so their views are gathered
	and generated in one left-padded batch (sub-batched into ``max_batch_size`` waves). The representative
	participant drives the batch — safe because a rollout's per-conversation participants wrap the *same* cached
	model + tokenizer. Message hooks still run per conversation before commit.
	"""
	if not convs:
		return convs
	n_parts = len(convs[0].participants)
	for i in range(turns):
		spk = i % n_parts
		batch_convs = [c for c in convs if _batchable(c.participants[spk])]
		other_convs = [c for c in convs if not _batchable(c.participants[spk])]
		for wave in _chunks(batch_convs, max_batch_size):
			if not wave:  # this round has no batchable speaker (e.g. an all-API/non-batch group) — nothing to fuse
				continue
			rep = wave[0].participants[spk]
			views = [c._view(c.participants[spk]) for c in wave]
			msgs = rep.generate_batch(views, turn=i, group_seed=group_seed + i)
			for c, msg in zip(wave, msgs):
				msg = c._apply_hooks(msg)
				if msg is not None:
					c.transcript.messages.append(msg)
		for c in other_convs:  # tools / API / human: correctness over throughput
			c.step(c.participants[spk])
	return convs
