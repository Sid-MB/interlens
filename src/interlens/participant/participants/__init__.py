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

# Concrete Participant implementations: the local-HF base (ModelParticipant) + per-family subclasses, and the
# hosted-API participant. Kept a real (non-namespace) package so static doc tooling (Griffe/mkdocstrings) and
# type checkers can resolve the submodules by dotted path; the public names are still re-exported from the
# top-level `interlens` package.
from .model_participant import ModelParticipant
from .qwen import QwenModelParticipant
from .gemma import GemmaModelParticipant
from .llama import LlamaModelParticipant
from .api_participant import APIParticipant

__all__ = ["ModelParticipant", "QwenModelParticipant", "GemmaModelParticipant", "LlamaModelParticipant", "APIParticipant"]
