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

"""Shared fixtures + lightweight fakes for the no-GPU chat-harness tests.

The fast suite never loads model weights: it drives the harness with ``StubParticipant`` (a ``Participant``
that returns a canned line) and ``FakeTokenizer`` (word-per-token length estimation), which is enough to
exercise the transcript/view/scenario/branch/stop/context/hook logic. Real-model behavior lives in the
``slow``-marked tests.
"""
from __future__ import annotations

import pytest

from interlens.message import Message
from interlens.participant import Participant


class FakeTokenizer:
	"""Counts one 'token' per whitespace word — enough for context-policy fitting decisions."""

	model_max_length = 10_000

	def __call__(self, text, add_special_tokens=False):
		class _Enc:
			pass
		enc = _Enc()
		enc.input_ids = text.split()
		return enc


class StubParticipant(Participant):
	"""A minimal participant: echoes a fixed line, records the last view it saw. Accepts (and ignores) the
	interp kwargs so it can stand in anywhere a real participant is called."""

	def __init__(self, name, system_prompt=None, private_context=(), reply=None):
		self.name = name
		self.system_prompt = system_prompt
		self.private_context = private_context
		self.tokenizer = FakeTokenizer()
		self._reply = reply
		self.last_view = None

	def generate(self, view, **kwargs):
		self.last_view = view
		return Message(self.name, self._reply if self._reply is not None else f"{self.name}-says")


@pytest.fixture
def stub():
	return StubParticipant


@pytest.fixture
def fake_tokenizer():
	return FakeTokenizer()
