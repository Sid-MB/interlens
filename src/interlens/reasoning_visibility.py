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

from __future__ import annotations

from enum import Enum


class ReasoningVisibility(str, Enum):
	"""Controls whether a participant's prior ``<think>`` reasoning is re-injected into views on later turns.

	Reasoning is always parsed out of ``Message.content`` into ``metadata['parsed_think']`` (so it is available
	for interpretability regardless of this setting). This enum only governs *history re-injection*:

	- ``STRIP`` (default): prior reasoning is dropped from all views — matches R1/Qwen3 chat templates, keeps
	  reasoning a genuinely private scratchpad the other participant never sees, and is always template-safe.
	- ``SELF_RETAIN``: a participant sees its *own* prior reasoning re-injected into its view (visible-scratchpad
	  self-continuation experiments).
	- ``SHARED``: all participants see all prior reasoning (shared-CoT collaboration/debate experiments).

	Non-STRIP modes re-inject reasoning as tagged text at render time so templates that reject a native prior
	``<think>`` turn don't error.
	"""

	STRIP = "strip"
	SELF_RETAIN = "self_retain"
	SHARED = "shared"
