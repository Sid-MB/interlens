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

"""Direct piping: a two-agent scripted dialogue where each turn's output is the next agent's input.

``DirectPipingPolicy`` formalizes the pipeline framing — participant i sees only its predecessor's output
(plus framing and its own turns) — and generalizes it to longer chains, where it genuinely diverges from a
shared transcript (in a 3-stage pipe, stage 3 never sees stage 1's raw output). This example runs entirely on
``ScriptedParticipant``s: no models, no network — run it to see the visibility semantics.

    python examples/arena_direct_piping.py
"""
from __future__ import annotations

from interlens import Conversation, DirectPipingPolicy, ScriptedParticipant


def main() -> None:
	# a 3-stage pipeline: drafter -> tightener -> fact-checker (scripted stand-ins)
	drafter = ScriptedParticipant(name="drafter", scripts=[
		"DRAFT: Interlens arena ships two scoreable multi-agent scenarios, both with exact solvers."])
	tightener = ScriptedParticipant(name="tightener", scripts=[
		"TIGHTENED: Arena ships two solver-verified multi-agent scenarios."])
	checker = ScriptedParticipant(name="checker", scripts=[
		"CHECKED: claim verified — two scenarios, both generators enumerate exactly."])

	conv = Conversation(participants=(drafter, tightener, checker),
	                    shared_context="Pipeline: draft, tighten, fact-check.",
	                    communication=DirectPipingPolicy())
	conv.run(turns=3)

	print(conv.transcript.pretty())
	print()
	# the pipeline property: the checker's view contains the tightened text, never the raw draft
	checker_view = "\n".join(m["content"] for m in conv.view("checker"))
	assert "TIGHTENED" in checker_view and "DRAFT:" not in checker_view
	print("checker saw the tightened text and never the raw draft — pipeline visibility holds.")


if __name__ == "__main__":
	main()
