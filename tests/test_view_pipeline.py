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

"""Family finalize (Gemma fold+merge+author-labels) and context policies operating on typed segments."""
from __future__ import annotations

import pytest

from interlens.participant.participants.gemma import GemmaModelParticipant
from interlens.view import ViewSegment
from interlens.context import ErrorPolicy, DropOldestPolicy, SlidingWindowPolicy, SummarizePolicy
from .conftest import FakeTokenizer


def _gemma():
	# Exercise finalize_view without a model. Flags are now tokenizer-derived at build time, so set the
	# Gemma-2 template semantics (no system role, strict alternation) directly on the instance under test.
	p = GemmaModelParticipant.__new__(GemmaModelParticipant)
	p.supports_system_role = False
	p.requires_alternating_roles = True
	return p


def test_gemma_folds_system_and_merges_same_role():
	segs = [
		ViewSegment("system", "SYS", "system"),
		ViewSegment("user", "moderator Q", "moderator", "moderator"),
		ViewSegment("user", "alice turn", "turn", "alice"),
		ViewSegment("assistant", "bob turn", "turn", "bob"),
	]
	out = _gemma().finalize_view(segs)
	assert all(m["role"] != "system" for m in out)            # system folded away
	assert [m["role"] for m in out] == ["user", "assistant"]  # consecutive users merged -> strict alternation
	assert "SYS" in out[0]["content"]                         # system folded into first user
	assert "moderator:" in out[0]["content"] and "alice: alice turn" in out[0]["content"]  # authors labelled


def _gemma3():
	# Gemma-3 template semantics: a leading system turn renders, but the turns after it must strictly alternate
	# and must START on user.
	p = GemmaModelParticipant.__new__(GemmaModelParticipant)
	p.supports_system_role = True
	p.requires_alternating_roles = True
	return p


def _permissive():
	p = GemmaModelParticipant.__new__(GemmaModelParticipant)
	p.supports_system_role = True
	p.requires_alternating_roles = False
	return p


def _alternates(messages) -> bool:
	"""The invariant a strict template asserts: after an optional leading system turn, user first, then strict
	user/assistant alternation."""
	roles = [m["role"] for m in messages]
	body = roles[1:] if roles[:1] == ["system"] else roles
	return "system" not in body and all(r == ("user" if i % 2 == 0 else "assistant") for i, r in enumerate(body))


# The shape that killed the P2 Gemma divide_dollar job: an arena scenario hands the participant an
# already-flattened per-seat view, and the round-1 OPENER's view begins with its own turn (its proposal is the
# first event in the shared log), so the first turn after system is `assistant` — which Gemma's template rejects
# with "Conversation roles must alternate user/assistant/...".
_OPENER_VIEW = [
	{"role": "system", "content": "SYS rules + your private sheet"},
	{"role": "assistant", "content": "my round-1 proposal"},
	{"role": "user", "content": "[Blake] counter\n\n[Casey] walk\n\nYour turn (round 2)."},
]


def test_repair_view_fixes_opener_view_starting_on_assistant():
	out = _gemma3().repair_view(_OPENER_VIEW)
	assert _alternates(out)
	assert out[0] == _OPENER_VIEW[0]                                     # system turn kept AS a system turn
	assert out[1]["role"] == "user"                                      # placeholder inserted, nothing re-roled
	assert out[2] == {"role": "assistant", "content": "my round-1 proposal"}  # own words never re-attributed
	assert out == _gemma3().repair_view(out)                             # idempotent


def test_repair_view_merges_a_seat_that_speaks_twice_in_a_row():
	# a rotation/round-boundary repeat (or propose-then-vote) puts two of the seat's OWN turns back to back
	view = [
		{"role": "system", "content": "SYS"},
		{"role": "user", "content": "[Blake] opening"},
		{"role": "assistant", "content": "my proposal"},
		{"role": "assistant", "content": "my vote"},
		{"role": "user", "content": "Your turn."},
	]
	out = _gemma3().repair_view(view)
	assert _alternates(out)
	merged = [m for m in out if m["role"] == "assistant"]
	assert len(merged) == 1 and "my proposal" in merged[0]["content"] and "my vote" in merged[0]["content"]


def test_repair_view_no_system_prepends_opening_user_turn():
	out = _gemma3().repair_view([{"role": "assistant", "content": "my turn"}, {"role": "user", "content": "go"}])
	assert _alternates(out) and out[1]["content"] == "my turn"


def test_repair_view_keeps_a_supported_system_turn_but_folds_an_unsupported_one():
	# the two flags are independent: the user-first repair must not cost a family its system role, and a family
	# without one must still end up with the framing in the opening user turn (nothing dropped either way)
	strict_with_system, no_system = _gemma3().repair_view(_OPENER_VIEW), _gemma().repair_view(_OPENER_VIEW)
	assert [m["role"] for m in strict_with_system][:2] == ["system", "user"]
	assert [m["role"] for m in no_system][:2] == ["user", "assistant"]
	assert all("SYS rules" in "".join(m["content"] for m in out) for out in (strict_with_system, no_system))


def test_repair_view_is_a_no_op_for_permissive_families():
	view = list(_OPENER_VIEW)
	assert _permissive().repair_view(view) == view


def test_repair_view_leaves_a_well_formed_view_untouched():
	view = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "hi"},
	        {"role": "assistant", "content": "me"}, {"role": "user", "content": "go"}]
	assert _gemma3().repair_view(view) == view


def test_no_system_role_family_folds_into_an_opening_user_turn_only():
	# Gemma-2 (no system role): the first user turn sits AFTER the seat's own turn, so folding into it would both
	# misplace the framing and leave the view starting on assistant — the system text opens the view instead.
	out = _gemma().repair_view(_OPENER_VIEW)
	assert _alternates(out)
	assert out[0]["role"] == "user" and out[0]["content"] == "SYS rules + your private sheet"


def _turns(n, words=10):
	return [ViewSegment("user", f"turn{i} " * words, "turn", "a") for i in range(n)]


def test_error_policy_raises_on_overflow():
	segs = [ViewSegment("system", "s " * 5, "system")] + _turns(5)
	with pytest.raises(ValueError):
		ErrorPolicy().fit(segs, FakeTokenizer(), limit=10)


def test_error_policy_passes_when_within_budget():
	segs = [ViewSegment("system", "s", "system")] + _turns(2, words=2)
	assert ErrorPolicy().fit(segs, FakeTokenizer(), limit=None) == segs


def test_sliding_window_keeps_system_and_recent():
	segs = [ViewSegment("system", "s " * 5, "system")] + _turns(5)
	kept = SlidingWindowPolicy(keep_last=2).fit(segs, FakeTokenizer(), limit=None)
	assert sum(1 for s in kept if s.origin == "system") == 1
	assert sum(1 for s in kept if s.origin == "turn") == 2


def test_drop_oldest_trims_to_budget_preserving_system():
	segs = [ViewSegment("system", "s " * 5, "system")] + _turns(5)
	kept = DropOldestPolicy().fit(segs, FakeTokenizer(), limit=30)
	assert any(s.origin == "system" for s in kept)
	assert sum(1 for s in kept if s.origin == "turn") < 5


def test_summarize_compresses_older_turns():
	segs = [ViewSegment("system", "s " * 3, "system"), ViewSegment("user", "seed", "moderator", "moderator")]
	segs += _turns(6, words=8)
	seen = {}
	kept = SummarizePolicy(keep_last=2, summarizer=lambda t: (seen.setdefault("n", len(t)), "SUMMARY")[1]) \
		.fit(segs, FakeTokenizer(), limit=30)
	assert sum(1 for s in kept if s.origin == "turn") == 2       # only last 2 verbatim
	assert any("SUMMARY" in s.content for s in kept)             # summary inserted
	assert seen["n"] == 4                                        # 6 - 2 kept = 4 summarized
