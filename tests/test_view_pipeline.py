"""Family finalize (Gemma fold+merge+author-labels) and context policies operating on typed segments."""
from __future__ import annotations

import pytest

from interlens.participant.participants.gemma import GemmaModelParticipant
from interlens.view import ViewSegment
from interlens.context import ErrorPolicy, DropOldestPolicy, SlidingWindowPolicy, SummarizePolicy
from .conftest import FakeTokenizer


def _gemma():
	return GemmaModelParticipant.__new__(GemmaModelParticipant)  # exercise finalize_view without a model


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
