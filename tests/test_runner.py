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

"""Runner (in-process path) + APIParticipant. No model weights: API participants use an injected fake client."""
from __future__ import annotations

import pytest

from interlens import APIParticipant, Conversation, run, register_analyzer, dataset_field


def _fake_client(system, messages, model, max_tokens, temperature):
	return f"[{model}] sys={bool(system)} n={len(messages)}"


def _conv(name=None):
	return Conversation(
		participants=[APIParticipant(name="a", model_id="m", client=_fake_client),
		              APIParticipant(name="b", model_id="m", client=_fake_client)],
		shared_context="hello",
	).turns(2).analyzer("count").name(name or "conv")


def test_api_participant_fake_client():
	api = APIParticipant(name="judge", model_id="claude-x", client=_fake_client)
	msg = api.generate([{"role": "system", "content": "be a judge"}, {"role": "user", "content": "hi"}])
	assert msg.author == "judge" and "claude-x" in msg.content and "sys=True" in msg.content


@pytest.mark.parametrize("kw", [
	{"capture": object()}, {"steering": object()}, {"patch": object()}, {"return_logprobs": True},
])
def test_api_participant_raises_on_interp(kw):
	api = APIParticipant(name="judge", model_id="m", client=_fake_client)
	with pytest.raises(NotImplementedError):
		api.generate([{"role": "user", "content": "hi"}], **kw)


register_analyzer("count", lambda conv: {"n": len(conv.transcript)})


def test_rollout_in_process_with_analyze(tmp_path):
	report = _conv().rollout(n=3, devices=["cpu"], out_dir=tmp_path)
	assert set(report.results) == {"rollout_0000", "rollout_0001", "rollout_0002"} and not report.failed
	assert all(r.analysis["n"] == 3 for r in report.results.values())   # seed + 2 turns
	assert all((tmp_path / jid / "transcript.json").exists() for jid in report.results)
	# rollout does not mutate the source recipe
	assert len(_conv().transcript) == 1


def test_rollout_resume_skips_completed(tmp_path):
	_conv().set(turns=1).rollout(n=2, devices=["cpu"], out_dir=tmp_path)
	report = _conv().set(turns=1).rollout(n=2, devices=["cpu"], out_dir=tmp_path, resume=True)
	assert set(report.skipped) == {"rollout_0000", "rollout_0001"} and not report.results


def test_failure_isolation(tmp_path):
	class _Boom(APIParticipant):
		def generate(self, *a, **k):
			raise RuntimeError("boom")
	good = _conv().name("good")
	bad = Conversation(participants=[_Boom(name="a", model_id="m", client=_fake_client),
	                                 APIParticipant(name="b", model_id="m", client=_fake_client)],
	                   shared_context="x").turns(1).name("bad")
	report = run([good, bad], devices=["cpu"], out_dir=tmp_path)
	assert report.results["good"].error is None
	assert report.results["bad"].error and "boom" in report.results["bad"].error
	assert report.failed == ["bad"]


def test_run_multi_lineup_namespaces_ids(tmp_path):
	report = run([_conv("solo"), _conv("pair")], devices=["cpu"], out_dir=tmp_path)
	assert set(report.results) == {"solo", "pair"} and not report.failed


def test_data_driven_rollout_per_row(tmp_path):
	conv = Conversation(
		participants=[APIParticipant(name="a", model_id="m", client=_fake_client)],
		shared_context=("Q: ", dataset_field("q")),
	).turns(1).data([{"q": "one"}, {"q": "two"}, {"q": "three"}]).analyzer("count")
	report = conv.rollout(devices=["cpu"], out_dir=tmp_path)
	assert set(report.results) == {"row_00000", "row_00001", "row_00002"}
	# each row's seed turn carries its own resolved question
	seeds = {jid: r.conversation.transcript[0].content for jid, r in report.results.items()}
	assert seeds["row_00000"] == "Q: one" and seeds["row_00002"] == "Q: three"
	# the source row reaches the analyzer via conv.row (per-row side data, not leaked into the model view)
	assert report.results["row_00001"].conversation.row["q"] == "two"


def test_data_driven_rollout_streams_iterable_without_len():
	# A bare generator (no __len__, no indexing) — the streaming IterableDataset shape — is consumed lazily.
	def rows():
		for q in ("alpha", "beta"):
			yield {"q": q}
	conv = Conversation(
		participants=[APIParticipant(name="a", model_id="m", client=_fake_client)],
		shared_context=("Q: ", dataset_field("q")),
	).turns(1).data(rows()).analyzer("count")
	report = conv.rollout(devices=["cpu"])
	assert set(report.results) == {"row_00000", "row_00001"}
	assert report.results["row_00000"].conversation.row["q"] == "alpha"
