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
	("Qwen/Qwen2.5-0.5B-Instruct", True, False),
]


@pytest.mark.parametrize("hf_id,exp_sys,exp_alt", _CASES)
def test_derive_chat_flags(hf_id, exp_sys, exp_alt):
	from transformers import AutoTokenizer

	tok = AutoTokenizer.from_pretrained(hf_id)
	assert derive_chat_flags(tok) == (exp_sys, exp_alt)
