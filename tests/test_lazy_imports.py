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

# [rational_agents: lazy-imports] 2026-07-31
# [implement: live-play/laneE] 2026-08-17

"""Pins the lazy public API of ``interlens`` (PEP 562 ``__getattr__`` over an explicit export table).

Two things must hold at once: the CPU-only entry points must not drag in ``torch`` / ``transformers``, and every
name that used to be importable from ``interlens`` must still be importable. The export list below is a frozen
copy of the eager ``__all__`` from before the change — it is the regression pin, so do not regenerate it from
``interlens.__all__``.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import interlens

# The exact set of names the eager ``__init__`` exposed (its ``__all__`` plus ``ScriptedParticipant``, which it
# imported but forgot to list). Every one of these must still resolve via attribute access.
LEGACY_EXPORTS = (
	"Message", "Transcript", "ContextItem", "Functional", "dataset_field", "DatasetField", "Conversation",
	"ReasoningVisibility", "ExecutionMode", "Participant", "ModelParticipant", "QwenModelParticipant",
	"GemmaModelParticipant", "LlamaModelParticipant", "APIParticipant", "OpenRouterRouting", "Provider",
	"ScriptedParticipant", "ContextPolicy", "ErrorPolicy", "DropOldestPolicy", "SlidingWindowPolicy",
	"SummarizePolicy", "MessageHook", "MessageHookResult", "HookAction", "StopCondition", "AnyStopCondition",
	"TurnStopCondition", "TokenStopCondition", "ElapsedTimeStopCondition", "StopStringCondition", "TokenBudget",
	"CommunicationPolicy", "RoundRobinPolicy", "DirectPipingPolicy", "MessagingPolicy", "UsageMeter",
	"CostBudget", "register_pricing", "transcript_usage", "ActivationCache", "CaptureSpec", "SteeringSpec",
	"Patch", "token_logprobs", "decoder_layers", "GradCaptureSpec", "GradForwardOutput", "forward_with_grad",
	"continuation_logprob", "soft_embed", "gumbel_softmax_tokens", "LinearBridge", "Tool", "ToolCall",
	"ToolResult", "ToolRegistry", "DEFAULT_REGISTRY", "available_devices", "run", "run_jobs", "RunResult",
	"RunReport", "register_analyzer", "register_worker_init", "conversation_from_models", "conversation_from_ids",
	"AutoModelParticipant", "ModelLike",
)

# Entry points that only read JSON / write HTML and must stay free of the model stack. ``arena.live`` belongs
# here for the same reason the visualizer does and one more: its lobby is opened on whatever machine is at hand,
# and importing torch to render a page of pickers would cost ten seconds on a host with no GPU to use anyway.
CPU_ONLY_MODULES = ("interlens", "interlens.arena.viz", "interlens.arena.negotiation.analysis",
                    "interlens.arena.live")


def in_fresh_process(code: str) -> str:
	"""Run ``code`` in a fresh interpreter (same venv) and return its stdout — the only honest way to ask what a
	module pulls into ``sys.modules``, since the pytest process has already imported everything."""
	proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
	assert proc.returncode == 0, proc.stderr
	return proc.stdout.strip()


# ------------------------------------------------------------------ laziness ---

@pytest.mark.parametrize("module", CPU_ONLY_MODULES)
def test_cpu_entry_points_do_not_import_the_model_stack(module):
	loaded = in_fresh_process(
		f"import sys, {module}\n"
		"print(sorted({m.split('.')[0] for m in sys.modules} & {'torch', 'transformers'}))"
	)
	assert loaded == "[]", f"importing {module} pulled in {loaded}"


def test_attribute_access_imports_the_model_stack_on_demand():
	# The other half of the contract: the heavy modules must still load when a model name is actually touched.
	loaded = in_fresh_process(
		"import sys, interlens\n"
		"interlens.ModelParticipant\n"
		"print(sorted({m.split('.')[0] for m in sys.modules} & {'torch', 'transformers'}))"
	)
	assert loaded == "['torch', 'transformers']"


# -------------------------------------------------------------- export table ---

@pytest.mark.parametrize("name", LEGACY_EXPORTS)
def test_every_legacy_export_still_resolves(name):
	assert getattr(interlens, name) is not None
	assert name in interlens.__all__


def test_getattr_caches_and_rejects_unknown_names():
	interlens.Message  # first access populates module globals
	assert "Message" in vars(interlens)
	with pytest.raises(AttributeError, match="no attribute 'NotAThing'"):
		interlens.NotAThing


def test_dir_lists_the_full_public_api():
	assert set(interlens.__all__) <= set(dir(interlens))


def test_type_checking_block_mirrors_the_export_table():
	"""The ``if TYPE_CHECKING:`` imports exist only for type checkers, so nothing at runtime would notice them
	drifting from ``_EXPORTS_BY_MODULE``. Compare the two by parsing the source."""
	source = Path(interlens.__file__).read_text()
	block = next(node for node in ast.parse(source).body
	             if isinstance(node, ast.If) and ast.unparse(node.test) == "TYPE_CHECKING")
	declared: dict[str, set[str]] = {}
	for stmt in block.body:
		if isinstance(stmt, ast.ImportFrom):
			key = "." * stmt.level + (stmt.module or "")
			declared.setdefault(key, set()).update(alias.name for alias in stmt.names)
	table = {module: set(names) for module, names in interlens._EXPORTS_BY_MODULE.items()}
	assert declared == table


# ----------------------------------------------------------- family registry ---

def test_family_registry_is_populated_without_eager_package_imports():
	"""``AutoModelParticipant`` resolves a family from ``ModelParticipant._REGISTRY``, which subclasses fill at
	class-creation time — so importing ``factories`` alone (the only consumer) must still see qwen/gemma/llama."""
	resolved = in_fresh_process(
		"from interlens.factories import AutoModelParticipant\n"
		"from interlens import ModelParticipant\n"
		"print([ModelParticipant.for_model_type(t).__name__ for t in ('qwen3', 'gemma3', 'llama', 'mystery')])"
	)
	assert resolved == "['QwenModelParticipant', 'GemmaModelParticipant', 'LlamaModelParticipant', "\
	                   "'ModelParticipant']"
