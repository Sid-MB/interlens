# [complete-chat-harness]: co-stepping batched runner (PLAN item 5 / CLUSTER_NEXT_STEPS item 5).
# Steps a group of independent conversations that SHARE participant/model objects in lockstep, batching each
# round's same-position turns into ONE model.generate — the biggest rollout throughput win. Throughput mode
# only: batch composition + the global RNG perturb rows, so tokens are NOT identical to unbatched (PLAN
# §Execution modes). Conversations that can't batch (tools, non-ModelParticipant speaker) fall back to the
# per-conversation .step within the same round, so a mixed group still runs correctly.
from __future__ import annotations

from ..participant.participants.model_participant import ModelParticipant


def _chunks(items, size):
	if not size or size <= 0 or size >= len(items):
		return [items]
	return [items[i:i + size] for i in range(0, len(items), size)]


def _batchable(participant) -> bool:
	# Plain ModelParticipant with no tools batches; tool loops / API / human speakers take the per-conv path.
	return type(participant).__name__ in ("ModelParticipant", "QwenModelParticipant", "GemmaModelParticipant") \
		and not getattr(participant, "tools", ())


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
