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
