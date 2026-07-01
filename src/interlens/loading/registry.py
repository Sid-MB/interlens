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

"""Internal model→participant resolution, keyed by the transformers ``config.model_type``.

This is the AutoModel-style dispatch behind ``AutoModelParticipant``: the family is read from the loaded
model's ``config.model_type`` (the canonical transformers family id — e.g. ``gemma2``, ``gemma3``, ``llama``,
``qwen2``), NOT from a short name or a hand-maintained registry. Only families whose *tool-call parsing* differs
from the base ``ModelParticipant`` need an entry here; everything else (Qwen, Mistral, OLMo, Phi, DeepSeek, …)
falls through to the base class. Chat-template flags (system-role support, strict alternation) are no longer
declared — they are derived directly from the tokenizer's own template via ``derive_chat_flags``, so an unknown
model type gets correct behavior with zero configuration.
"""
from __future__ import annotations

from ..participant.participants.model_participant import ModelParticipant
from ..participant.participants.gemma import GemmaModelParticipant
from ..participant.participants.llama import LlamaModelParticipant

# Only families whose tool-call parsing diverges from base need a row; all others use ModelParticipant.
_PARTICIPANT_BY_MODEL_TYPE: dict[str, type[ModelParticipant]] = {
	"gemma2": GemmaModelParticipant,
	"gemma3": GemmaModelParticipant,
	"llama": LlamaModelParticipant,
}


def participant_class_for(model_type: str | None) -> type[ModelParticipant]:
	"""The participant class for a transformers ``config.model_type``, falling back to the base ``ModelParticipant``
	for any family without a specialized tool-call parser (or an unknown/missing type)."""
	return _PARTICIPANT_BY_MODEL_TYPE.get(model_type or "", ModelParticipant)


def derive_chat_flags(tokenizer) -> tuple[bool, bool]:
	"""Probe a tokenizer's chat template to derive ``(supports_system_role, requires_alternating_roles)``.

	``supports_system_role`` is True iff the template renders a leading ``system`` turn without raising;
	``requires_alternating_roles`` is True iff the template rejects two consecutive same-role turns. Each probe is
	wrapped in try/except so a raising template simply reads as the corresponding boolean."""

	def _renders(messages) -> bool:
		try:
			tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
			return True
		except Exception:
			return False

	supports_system_role = _renders([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}])
	requires_alternating_roles = not _renders([{"role": "user", "content": "a"}, {"role": "user", "content": "b"}])
	return supports_system_role, requires_alternating_roles
