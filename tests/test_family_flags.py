"""Verify each generation's *declared* chat-template flags match what its tokenizer's template actually does.

The registry hand-declares capability flags per participant class (``supports_system_role``,
``requires_alternating_roles``) and maps several generations onto the same class (e.g. ``gemma2`` and ``gemma3``
both use ``GemmaModelParticipant``). Nothing guarantees two generations share a template — so this test loads each
generation's real tokenizer and asserts the declared flags equal the template's observed behavior. If a new
generation diverges (e.g. Gemma 3 starts accepting a system role), this fails loudly instead of silently
mis-flattening prompts.

Opt-in (loads tokenizers over the network):

    uv run pytest tests/test_family_flags.py -m slow
"""
from __future__ import annotations

import pytest

from interlens.loading import MODELS, resolve, participant_class

pytestmark = pytest.mark.slow

# One representative model per generation (all sizes of a generation share the template/flags).
_REPS: dict[str, str] = {}
for _name, _spec in MODELS.items():
	_REPS.setdefault(_spec.generation, _name)


def _accepts(tokenizer, messages) -> bool:
	"""True iff the chat template renders ``messages`` without raising."""
	try:
		tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
		return True
	except Exception:
		return False


@pytest.mark.parametrize("generation,model", sorted(_REPS.items()))
def test_declared_flags_match_template(generation, model):
	from transformers import AutoTokenizer

	hf_id, gen = resolve(model)
	assert gen == generation  # the registry MODELS->generation mapping is self-consistent
	cls = participant_class(model)
	tok = AutoTokenizer.from_pretrained(hf_id)

	# supports_system_role: does the template accept a standalone leading `system` message?
	template_supports_system = _accepts(tok, [{"role": "system", "content": "S"}, {"role": "user", "content": "hi"}])
	# requires_alternating_roles: does the template REJECT two consecutive same-role turns?
	template_requires_alternating = not _accepts(tok, [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}])

	assert cls.supports_system_role == template_supports_system, (
		f"{generation} ({cls.__name__}): declared supports_system_role={cls.supports_system_role} but the "
		f"{hf_id} template {'accepts' if template_supports_system else 'rejects'} a standalone system role"
	)
	assert cls.requires_alternating_roles == template_requires_alternating, (
		f"{generation} ({cls.__name__}): declared requires_alternating_roles={cls.requires_alternating_roles} but the "
		f"{hf_id} template {'rejects' if template_requires_alternating else 'accepts'} consecutive same-role turns"
	)
