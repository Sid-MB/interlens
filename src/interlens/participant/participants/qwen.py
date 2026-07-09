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

from typing import ClassVar

from .model_participant import ModelParticipant

class QwenModelParticipant(ModelParticipant):
	"""A participant in a conversation that is a Qwen language model. Its tool-call format is the Hermes/base
	``<tool_call>`` JSON already handled by ``ModelParticipant``, so this class adds no behavior — it exists so
	Qwen models resolve to a distinct, statically-typed participant class."""

	MODEL_TYPES: ClassVar[frozenset[str]] = frozenset({"qwen2", "qwen3", "qwen3_5", "qwen3_5_moe"})
