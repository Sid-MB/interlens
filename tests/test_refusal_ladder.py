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

"""The API-refusal re-render ladder: content preservation, determinism, and the engine wiring that commits the
recovered turn and stamps which rung cleared it."""
from __future__ import annotations

import asyncio
import re

import pytest

from interlens.arena import EpisodePool, EpisodeStore, RefusalLadder, is_refusal
from interlens.arena.scenarios import InfoRelay
from interlens.message import Message
from interlens.participant import Participant

VIEW = [
	{"role": "system", "content": "You are the regional operator."},
	{"role": "user", "content": (
		"Turn 7 of this auction.\n\n"
		"## Catalogue -- stage 2 of 6\n| lot | base |\n|---|---|\n| Lot 1 | 90 |\n| Lot 2 | 117 |\n\n"
		"## What has happened so far\nStage 1 cleared at 143 to the hyperscaler.\n\n"
		"## Your private position\nLot 1 is worth 104 to you. Budget 380.\n\n"
		"## This round\nStanding high on Lot 1 is 96.\n\n"
		"Reply now with one fenced JSON object.")},
]

NUMBERS = re.compile(r"\d+")


def _numbers(text: str) -> list[str]:
	return NUMBERS.findall(text)


@pytest.mark.parametrize("rung", [1, 2, 3])
def test_every_rung_preserves_every_number_and_every_body_line(rung):
	"""The ladder's whole claim is that a recovered turn conditions on the same content. Rungs may move blocks,
	re-wrap headings, and add an inert tag line -- they may never change a number or a body line, or the
	recovered turn would be a different decision problem than the refused one."""
	out = RefusalLadder().perturb(VIEW, rung, key="ep-1/regional_operator/7/turn")
	before, after = VIEW[1]["content"], out[1]["content"]
	# The nonce tag is hexadecimal and the only new digits; strip that line before comparing.
	after_body = "\n".join(ln for ln in after.split("\n") if not ln.startswith("Protocol note:"))
	assert sorted(_numbers(after_body)) == sorted(_numbers(before))
	body_lines = {ln for ln in before.split("\n") if not ln.startswith("## ")}
	assert body_lines <= set(after_body.split("\n"))
	assert out[0] == VIEW[0]                 # the system prompt is never touched
	assert VIEW[1]["content"] == before      # and the input view is not mutated


def test_rungs_escalate_and_replay_identically():
	"""Rungs are cumulative and seeded: rung 2 differs from rung 1, and the same key gives the same bytes, which
	is what makes a recovered turn reproducible from the episode record."""
	ladder = RefusalLadder()
	key = "ep-1/regional_operator/7/turn"
	texts = [ladder.perturb(VIEW, k, key=key)[1]["content"] for k in (1, 2, 3)]
	assert len({*texts}) == 3
	assert texts[0] == ladder.perturb(VIEW, 1, key=key)[1]["content"]
	assert texts[1] != ladder.perturb(VIEW, 2, key="ep-1/hyperscaler/7/turn")[1]["content"]
	assert texts[0].splitlines()[0].startswith("Protocol note: request variant ")
	assert "### Section: Catalogue -- stage 2 of 6" in texts[2]
	with pytest.raises(ValueError):
		ladder.perturb(VIEW, 4, key=key)


def test_permutation_holds_the_header_and_the_ask_in_place():
	"""The first block carries the turn marker and the last is the single closing ask; both are position-
	dependent, and only the interior sections are independent of order."""
	text = RefusalLadder().perturb(VIEW, 2, key="k")[1]["content"]
	blocks = [b for b in text.split("\n\n") if b.strip()]
	assert blocks[0].startswith("Protocol note:")           # rung 1 rides on top
	assert blocks[1].startswith("Turn 7 of this auction.")
	assert blocks[-1] == "Reply now with one fenced JSON object."
	interior = [b for b in VIEW[1]["content"].split("\n\n") if b.strip()][1:-1]
	assert sorted(blocks[2:-1]) == sorted(interior)     # the same sections, reordered and nothing else


def test_is_refusal_distinguishes_declined_from_truncated():
	assert is_refusal(Message("s", "", {"stop_reason": "refusal"}))
	assert is_refusal(Message("s", "", {"refusal": True, "stop_reason": None}))
	assert is_refusal(Message("s", "   ", {"stop_reason": None}))
	# A cap hit is a token-floor problem, not something a re-render can fix, so the ladder leaves it alone.
	assert not is_refusal(Message("s", "", {"stop_reason": "max_tokens"}))
	assert not is_refusal(Message("s", '{"action": "pass"}', {"stop_reason": "end_turn"}))


class RefusingSeat(Participant):
	"""Refuses every request whose user turn matches the ORIGINAL bytes, and answers any re-render. This is the
	measured shape of the failure: deterministic on byte-identical requests, cleared by re-rendering."""

	def __init__(self, clears_at_rung: int = 1, text: str = "Here is what my notes say."):
		self.name = "refuser"
		self.clears_at_rung = clears_at_rung
		self.text = text
		self.calls = 0
		self.seen: list[str] = []

	def generate(self, view, *, max_new_tokens=None, **kwargs):
		self.calls += 1
		user = view[-1]["content"]
		self.seen.append(user)
		# rung k's view carries k perturbations; count them the way the ladder applies them.
		rung = (user.startswith("Protocol note:") + ("### Section:" in user)
		        + (self.clears_at_rung > 1 and "Protocol note:" in user))
		if rung >= self.clears_at_rung:
			return Message(self.name, self.text, {"n_tokens": 10, "n_tokens_in": 50, "stop_reason": "end_turn"})
		return Message(self.name, "", {"n_tokens": 0, "n_tokens_in": 50, "stop_reason": "refusal",
		                               "refusal": True})


def test_engine_commits_the_recovered_turn_and_stamps_the_rung(tmp_path):
	"""End to end: with a ladder installed, a refusing participant's episode completes, the committed turns are
	the RE-RENDERED ones (their recorded view is what the seat actually read), and each carries the rung that
	cleared it. Without a ladder the same participant produces empty turns."""
	scn = InfoRelay()
	inst = scn.generate_instance(0, 11)
	seat = RefusingSeat()
	pool = EpisodePool(EpisodeStore(tmp_path / "eps"), max_concurrent=2, refusal_ladder=RefusalLadder())
	ep = asyncio.run(pool.run_episode(scn, inst, "team", seat, seed=0))
	assert ep.status == "done"
	stamped = [t for t in ep.turns if t.refusal_recovery]
	assert stamped, "every refused turn must carry a recovery record"
	assert all(t.refusal_recovery["outcome"] == "recovered" for t in stamped)
	assert all(t.refusal_recovery["rung"] == 1 for t in stamped)
	assert all(t.refusal_recovery["attempts"] == ["nonce"] for t in stamped)
	assert all(t.view[-1]["content"].startswith("Protocol note:") for t in stamped)
	assert seat.calls == 2 * len(stamped) or seat.calls > len(stamped)


def test_a_view_that_refuses_at_every_rung_is_terminal_not_silently_passed(tmp_path):
	"""If no rung clears it, the ladder says so: the turn is stamped ``terminal`` with every rung it tried, so a
	cell's validity gate sees a turn no model produced rather than a fallback move nobody chose."""
	scn = InfoRelay()
	inst = scn.generate_instance(0, 11)
	seat = RefusingSeat(clears_at_rung=99)
	pool = EpisodePool(EpisodeStore(tmp_path / "eps"), max_concurrent=2, refusal_ladder=RefusalLadder())
	ep = asyncio.run(pool.run_episode(scn, inst, "team", seat, seed=0))
	stamped = [t for t in ep.turns if t.refusal_recovery]
	assert stamped
	assert all(t.refusal_recovery == {"outcome": "terminal", "rung": None,
	                                  "attempts": ["nonce", "permute", "reframe"]} for t in stamped)
