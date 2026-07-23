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

# [rational_agents scaffold: scenario-runner] 2026-07-23 — canonical prompt scaffold for ScorableNegotiation.

"""The canonical prompt scaffold for the scorable-negotiation scenario.

Prompt configuration is a *documented confound*: in the scoreable-games literature the choice of
chain-of-thought scaffold swings the same model's success rate 15%->81% (Abdelnabi et al. 2309.17234) with
20-50 point swings across configs, and the best config is model-dependent (TMLR [Re] BVH81SAAh2). So this
module fixes exactly ONE canonical wording, and every knob that changes the wording is an explicit field on
:class:`PromptScaffold` — an experiment ablates prompt wording by constructing a variant scaffold, never by
editing the scenario. The scenario (:class:`~interlens.arena.scenarios.scorable.ScorableNegotiation`) holds a
scaffold and calls its render methods; :data:`DEFAULT_SCAFFOLD` is the blessed default.

Design rules baked in (each traceable to a peer-reviewed critique — see
``experiments/rational_agents/docs/lit/benchmarks-scorable-games.md`` "Design Lessons"):

- **Structural channel separation** (Lesson 11): a turn is one fenced JSON object with three fields —
  ``scratchpad`` (private, never published), ``message`` (public cheap talk), ``action`` (the formal move).
  The harness publishes ONLY ``message`` + a rendering of the validated ``action``. Privacy never depends on
  the model's tag discipline, so a model that dumps its score numbers into ``scratchpad`` cannot leak them
  (numbers put in ``message`` are genuine strategic disclosure — a measured failure, not a parse artifact).
- **Formal votes, offer ids** (Lessons 7, 10): accepts reference a specific live offer id; a deal closes only
  by real unanimous ACCEPT of one standing offer, never by arithmetic on a final proposal.
- **Turn-count deadline restated every turn** (Lesson 13): ``turn_prompt`` always restates the round budget.
- **De-anchoring** (Lesson 5): issue/option labels come from the instance (fictional units), not from here.
- **Preference/role decorrelation knob** (Lesson 4): ``role_lines`` are OFF by default so public role text
  can't leak private preferences; turn on only to measure the leak.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# The four formal moves (Fatima-Wooldridge-Jennings AIJ 2004 package deals; LLM-X 2605.11376 offer-id accepts)
# plus an explicit talk-only pass, so a party can speak without moving without emitting a spurious action.
ACTION_TYPES = ("propose", "accept", "reject", "walk", "none")


def _fence(obj_text: str) -> str:
	"""Wrap a JSON snippet in a ```json fenced block (the one action format the parser reads)."""
	return f"```json\n{obj_text}\n```"


@dataclass(frozen=True)
class PromptScaffold:
	"""One immutable prompt wording. Construct a variant to ablate wording; never edit the scenario.

	All game *content* (issue names, option labels, party names, sheets, thresholds, round budget, info
	condition, chat flag) is passed into the render methods by the scenario — this object holds only the
	fixed *wording* around that content, so a single scaffold renders any instance. Every field below is a
	template fragment or a toggle; the render methods assemble them.

	Fields
	------
	game_intro : str
		One-line framing of what the parties are doing; ``{n}`` is the party count. Deliberately generic /
		de-anchored — the concrete subject matter lives in the (fictional) issue labels.
	scratchpad_help, message_help, action_help : str
		The per-field guidance in the action-format block.
	worked_examples : bool
		Include the two worked-example JSON blocks (propose-with-message, accept). On by default — worked
		examples materially raise format compliance for smaller models; turn off to ablate.
	include_pass : bool
		Advertise the talk-only ``{"type": "none"}`` move. On by default so talking without moving is explicit
		rather than smuggled into a malformed action.
	show_role_lines : bool
		Render each party's public role description (which can leak preferences). OFF by default to keep sheets
		decorrelated from public text (the communication-free-baseline leak, Study A 2502.16242). Turn on only
		to *measure* the leak.
	"""

	game_intro: str = ("You are one of {n} parties negotiating a single multi-issue agreement. "
	                   "Exactly one option must be chosen for every issue; the chosen options together "
	                   "form the deal.")
	scratchpad_help: str = ("private notes to yourself. NEVER shown to any other party. Reason here freely — "
	                        "writing here is not speaking and costs you nothing.")
	message_help: str = ("a short statement spoken aloud to every party (cheap talk — it does not bind you). "
	                     "Do NOT put your private score numbers here.")
	action_help: str = "exactly one formal move this turn."
	worked_examples: bool = True
	include_pass: bool = True
	show_role_lines: bool = False

	# ---------------------------------------------------------------- pieces --
	def rules_block(self, *, n: int, party_lines: list[str], issue_lines: list[str],
	                proposer_order: list[str], rounds: int, veto_line: str, pass_rule: str) -> str:
		"""The public, common-knowledge rules every seat sees: parties, issues+options, turn/deadline
		protocol, and the exact deal-closing rule. ``party_lines`` already includes role text iff
		``show_role_lines``; ``issue_lines`` are ``"- Name: OptA, OptB, ..."`` rendered by the scenario."""
		order = ", ".join(proposer_order)
		return "\n".join([
			self.game_intro.format(n=n),
			"",
			"Parties at the table:",
			*party_lines,
			"",
			"Issues (choose exactly one option each):",
			*issue_lines,
			"",
			f"Protocol: turns are taken in a fixed rotation ({order}); the party who tables the opening "
			f"proposal rotates from round to round. There are {rounds} rounds of turns in total.",
			pass_rule,
			veto_line,
		]).replace("\n\n\n", "\n\n")

	def action_format_block(self, *, chat_enabled: bool) -> str:
		"""The single action-format contract + worked examples. ``chat_enabled`` toggles the public message
		channel (moves-only arm disables it — a ``message`` field is then ignored by the harness).

		The wire form is ONE flat fenced JSON object: a string ``"action"`` field with its parameters as
		siblings (``"deal"`` / ``"offer_id"``), alongside the private ``"scratchpad"`` and public ``"message"``
		channels. This matches the shared typed-action parser (``interlens.arena.actions.parse_action``)."""
		lines = ["On your turn, reply with EXACTLY ONE fenced JSON object and nothing outside it:"]
		if chat_enabled:
			shape = ('{"scratchpad": "...", "message": "...", '
			         '"action": "propose", "deal": {"<Issue>": "<Option>", ...}}')
		else:
			shape = '{"scratchpad": "...", "action": "propose", "deal": {"<Issue>": "<Option>", ...}}'
		lines.append(_fence(shape))
		lines.append("Fields:")
		lines.append(f'- "scratchpad" (optional): {self.scratchpad_help}')
		if chat_enabled:
			lines.append(f'- "message" (optional): {self.message_help}')
		else:
			lines.append('- There is NO public message channel in this game; a "message" field is ignored.')
		lines.append(f'- "action" (required): a string naming {self.action_help} With its parameters as siblings:')
		lines.append('    - "propose" + "deal": {every issue -> one option} — tables a complete package; the '
		             "mediator gives it an offer id (P1, P2, ...) and records you as supporting it.")
		lines.append('    - "accept" + "offer_id": "<id>" — formally accept a specific live offer by its id. A '
		             "deal closes ONLY when every other still-active party has accepted the SAME live offer, so "
		             "your accept is a real vote.")
		lines.append('    - "reject" + "offer_id": "<id>" — formally reject a specific live offer.')
		lines.append('    - "walk" — leave the table permanently; you take the no-deal outcome and no further '
		             "turns.")
		if self.include_pass:
			lines.append('    - "none" — make no formal move this turn (you may still speak, if the message '
			             "channel is open). Omitting the action entirely means the same.")
		if self.worked_examples:
			lines.append("")
			lines.append("Worked example — tabling a package while making your case:")
			ex1 = ('{"scratchpad": "Option B on Site is my best; I can give on Timeline.", '
			       '"message": "I can back a package built on Site=B if the timeline stays tight.", '
			       '"action": "propose", "deal": {"Site": "B", "Timeline": "Tight"}}')
			if not chat_enabled:
				ex1 = ('{"scratchpad": "Option B on Site is my best; I can give on Timeline.", '
				       '"action": "propose", "deal": {"Site": "B", "Timeline": "Tight"}}')
			lines.append(_fence(ex1))
			lines.append("Worked example — accepting a live offer by id:")
			ex2 = ('{"message": "P2 clears my bar. I accept.", "action": "accept", "offer_id": "P2"}'
			       if chat_enabled else '{"action": "accept", "offer_id": "P2"}')
			lines.append(_fence(ex2))
		lines.append("")
		lines.append("Rules of the road:")
		lines.append("- Your acceptance threshold is private. A deal scoring below it is worse for you than no "
		             "deal — never propose or accept a package below your threshold.")
		lines.append('- Accepts MUST name a live offer id; "I accept" with no id does nothing.')
		lines.append("- Reply with ONLY the fenced JSON object.")
		return "\n".join(lines)

	def private_block(self, *, seat: str, role_desc: str, sheet_lines: list[str], threshold: float,
	                  persona: str | None) -> str:
		"""The seat's private framing: who it is, its secret score sheet, its threshold, optional persona.
		``sheet_lines`` are ``"- Issue: OptA=12, OptB=0, ..."`` rendered by the scenario."""
		who = f"You are {seat}" + (f" ({role_desc})" if role_desc else "") + "."
		lines = [
			"=== PRIVATE — yours alone; never reveal these numbers verbatim ===",
			who,
			"Your secret score sheet (points you get for each option):",
			*sheet_lines,
			f"Your acceptance threshold: {threshold:g} points. A deal scoring below this is worse for you "
			"than no deal at all.",
			"Your total for a deal is the sum of your points for the chosen options.",
		]
		if persona:
			lines.append(persona)
		return "\n".join(lines)

	def info_condition_note(self, *, info: str) -> str:
		"""The one line describing what a seat knows about others' sheets (FULL vs PRIVATE)."""
		if info == "full":
			return ("Information: every party's score sheet is common knowledge and is listed below — there "
			        "is no private information, so any inefficiency is a pure negotiation failure.")
		return ("Information: every other party's score sheet is private to them. You know only that each was "
		        "drawn from the shared, publicly-known distribution described in the rules.")

	# ------------------------------------------------------------ assembled --
	def system_prompt(self, *, rules: str, private: str, action_format: str, info_note: str,
	                  full_info_sheets: str | None) -> str:
		"""Assemble a seat's complete system prompt. ``full_info_sheets`` is the block of all parties' sheets,
		present only in the FULL-information condition."""
		parts = [rules, "", info_note]
		if full_info_sheets:
			parts += ["", "All parties' score sheets (common knowledge):", full_info_sheets]
		parts += ["", private, "", action_format]
		return "\n".join(parts)

	def turn_prompt(self, *, seat: str, round_no: int, rounds: int, is_opener: bool,
	                offers_block: str, chat_enabled: bool) -> str:
		"""The per-turn user prompt: restates the deadline (Lesson 13), lists live offers with ids, and names
		whose turn it is. ``offers_block`` is the scenario-rendered live-offers summary (with, privately, this
		seat's own score for each live offer when the scenario surfaces it)."""
		head = f"[Mediator] Round {round_no} of {rounds}. It is your turn, {seat}."
		if is_opener:
			head += " You hold the opening proposal this round."
		body = [head, offers_block]
		if chat_enabled:
			body.append("Speak to the table and/or take one formal action, as one fenced JSON object.")
		else:
			body.append("Take one formal action, as one fenced JSON object (no public message channel).")
		return "\n".join(x for x in body if x)

	def final_prompt(self, *, seat: str, offers_block: str) -> str:
		"""The forced-final prompt when the round budget is exhausted with no deal: the current opener must
		either table a last binding proposal or walk."""
		return "\n".join([
			f"[Mediator] The rounds are over with no agreement, {seat}. Make your FINAL move: either table one "
			"last complete proposal for an immediate up/down vote, or walk.",
			offers_block,
			'Reply with one fenced JSON object: {"action": "propose", "deal": {all issues}} or '
			'{"action": "walk"}.',
		])

	# -------------------------------------------------------------- solo arm --
	def solo_system_prompt(self, *, n: int, rules: str, all_sheets: str, threshold_note: str,
	                       pass_rule: str) -> str:
		"""The communication-free control (Study A 2502.16242): ONE agent with every sheet, proposing alone.
		This baseline must NOT be competitive with the full multi-agent game — if it is, the benchmark is
		measuring feasible-set search, not negotiation."""
		return "\n".join([
			f"You are a neutral mediator with FULL knowledge of all {n} parties' secret score sheets and the "
			"shared acceptance rule. There is no negotiation and no dialogue — you alone choose the deal.",
			"",
			rules,
			"",
			"All parties' score sheets:",
			all_sheets,
			"",
			threshold_note,
			pass_rule,
			"",
			"Work step by step if useful. When you are confident, reply with ONLY a fenced JSON object: "
			'{"action": "propose", "deal": {every issue -> one option}}.',
		])

	def solo_turn_prompt(self, *, forced: bool) -> str:
		"""The solo agent's per-step nudge; ``forced`` is the budget-exhausted last call."""
		if forced:
			return ('Stop now and answer. Reply with ONLY {"action": "propose", "deal": {...}}.')
		return ('Continue. When confident, reply with ONLY {"action": "propose", "deal": {...}}.')


# The one blessed wording. Experiments select this (or an explicit variant) via
# experiments/rational_agents/prompts.py; the scenario defaults to it.
DEFAULT_SCAFFOLD = PromptScaffold()
