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

"""Runner (in-process path) + APIParticipant. No model weights: API participants use an injected fake client."""
from __future__ import annotations

import pytest

from interlens import (
	APIParticipant, APIParticipantConfig, ConversationTemplate, ConversationSpec,
	run_conversations, register_analyzer,
)


def _fake_client(system, messages, model, max_tokens, temperature):
	return f"[{model}] sys={bool(system)} n={len(messages)}"


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


class _EchoConfig(APIParticipantConfig):
	"""API config that injects the fake client post-build, so specs run with no network/model."""

	def build(self, device, registry=None):
		p = super().build(device, registry)
		p.client = _fake_client
		return p


def _template():
	return ConversationTemplate(
		participants=[_EchoConfig(name="a", model_id="m"), _EchoConfig(name="b", model_id="m")],
		shared_context="hello", turns=2,
	)


def test_run_conversations_in_process_with_analyze(tmp_path):
	register_analyzer("count", lambda conv: {"n": len(conv.transcript)})
	specs = [ConversationSpec(template=_template(), job_id=f"job_{i}", turns=2) for i in range(3)]
	report = run_conversations(specs, devices=["cpu"], analyze="count", out_dir=tmp_path, in_process=True)
	assert set(report.results) == {"job_0", "job_1", "job_2"} and not report.failed
	assert all(r.analysis["n"] == 3 for r in report.results.values())   # seed + 2 turns
	assert all((tmp_path / jid / "transcript.json").exists() for jid in report.results)


def test_resume_skips_completed(tmp_path):
	specs = [ConversationSpec(template=_template(), job_id=f"job_{i}", turns=1) for i in range(2)]
	run_conversations(specs, devices=["cpu"], out_dir=tmp_path, in_process=True)
	report = run_conversations(specs, devices=["cpu"], out_dir=tmp_path, resume=True, in_process=True)
	assert set(report.skipped) == {"job_0", "job_1"} and not report.results


def test_failure_isolation(tmp_path):
	class _Boom(_EchoConfig):
		def build(self, device, registry=None):
			raise RuntimeError("boom")
	bad_tmpl = ConversationTemplate(participants=[_Boom(name="a", model_id="m"), _EchoConfig(name="b", model_id="m")],
	                                shared_context="x", turns=1)
	specs = [
		ConversationSpec(template=_template(), job_id="good", turns=1),
		ConversationSpec(template=bad_tmpl, job_id="bad", turns=1),
	]
	report = run_conversations(specs, devices=["cpu"], out_dir=tmp_path, in_process=True)
	assert report.results["good"].error is None
	assert report.results["bad"].error and "boom" in report.results["bad"].error
	assert report.failed == ["bad"]
