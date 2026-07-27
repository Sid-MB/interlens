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

"""Verify ``derive_chat_flags`` reads real tokenizer templates correctly.

Chat-template flags (``supports_system_role``, ``requires_alternating_roles``) are no longer hand-declared —
they are probed from the tokenizer's own template by ``derive_chat_flags``. This test loads a few representative
tokenizers and asserts the derived flags match the known behavior of each family (e.g. Gemma 2 rejects a system
role and requires strict alternation; Gemma 3 accepts a system role; Qwen accepts both).

Opt-in (loads tokenizers over the network):

    uv run pytest tests/test_family_flags.py -m slow
"""
from __future__ import annotations

import pytest

from interlens.loading import derive_chat_flags

pytestmark = pytest.mark.slow

# (hf_id, expected_supports_system_role, expected_requires_alternating_roles)
_CASES = [
	("google/gemma-2-2b-it", False, True),
	("google/gemma-3-4b-it", True, True),
	# Mistral phrases the same rule as "After the optional system message, conversation roles must alternate ..."
	# — a second, independently-templated strict family, so the repairs must be flag-driven, not Gemma-shaped.
	("mistralai/Ministral-8B-Instruct-2410", True, True),
	("Qwen/Qwen2.5-0.5B-Instruct", True, False),
]


@pytest.mark.parametrize("hf_id,exp_sys,exp_alt", _CASES)
def test_derive_chat_flags(hf_id, exp_sys, exp_alt):
	from transformers import AutoTokenizer

	tok = AutoTokenizer.from_pretrained(hf_id)
	assert derive_chat_flags(tok) == (exp_sys, exp_alt)


# An arena scenario hands a participant an already-flattened per-seat view, and a multi-round game's OPENER sees
# its own turn first (system, assistant, user, ...) — which every strict template rejects. ``repair_view`` (driven
# by the same derived flags) must make each of these render under the family's REAL template.
_ARENA_VIEWS = [
	[{"role": "system", "content": "SYS"}, {"role": "assistant", "content": "my proposal"},
	 {"role": "user", "content": "[Blake] counter\n\nYour turn."}],                                    # opener
	[{"role": "system", "content": "SYS"}, {"role": "user", "content": "[Blake] open"},
	 {"role": "assistant", "content": "propose"}, {"role": "assistant", "content": "vote"},
	 {"role": "user", "content": "Your turn."}],                                                       # spoke twice
]


@pytest.mark.parametrize("hf_id,_sys,_alt", _CASES)
@pytest.mark.parametrize("view", _ARENA_VIEWS)
def test_repaired_arena_views_render_under_real_templates(hf_id, _sys, _alt, view):
	from transformers import AutoTokenizer

	from interlens.participant.participants.gemma import GemmaModelParticipant

	tok = AutoTokenizer.from_pretrained(hf_id)
	p = GemmaModelParticipant.__new__(GemmaModelParticipant)
	p.supports_system_role, p.requires_alternating_roles = derive_chat_flags(tok)
	rendered = tok.apply_chat_template(p.repair_view(view), tokenize=False, add_generation_prompt=True)
	assert "my proposal" in rendered or "propose" in rendered   # the seat's own turn survived the repair
