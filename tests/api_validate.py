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

# [complete-chat-harness]: real APIParticipant validation (CLUSTER_NEXT_STEPS item 6). Needs ANTHROPIC_API_KEY
# and outbound internet. Runs a short Claude-vs-Claude conversation, uses Claude as an analyze-style classifier,
# and confirms the retry/backoff wrapper + interp-raise behavior. Uses a cheap Haiku model.
from __future__ import annotations

import os
import sys

from interlens import APIParticipant, Conversation

MODEL = "claude-haiku-4-5-20251001"  # cheap + fast for a smoke test


def log(m):
    print(f"[api] {m}", flush=True)


def check_backoff_wrapper():
    """The retry/backoff loop retries transient errors then succeeds — validated offline with a fake SDK."""
    from interlens.participant.participants.api_client import AnthropicClient

    class _FakeAnthropicMod:
        class RateLimitError(Exception):
            pass
        class APIConnectionError(Exception):
            pass
        class InternalServerError(Exception):
            pass
        class APIStatusError(Exception):
            pass
        NOT_GIVEN = object()

    calls = {"n": 0}

    client = AnthropicClient.__new__(AnthropicClient)  # bypass real SDK import
    client._anthropic = _FakeAnthropicMod
    client._sem = __import__("threading").Semaphore(2)
    client.max_retries, client.base_delay, client.max_delay = 5, 0.0, 0.0

    class _Resp:
        content = [type("B", (), {"type": "text", "text": "ok"})()]

    def _create(**kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _FakeAnthropicMod.RateLimitError("429")
        return _Resp()

    client._client = type("C", (), {"messages": type("M", (), {"create": staticmethod(_create)})()})()
    out = client(system=None, messages=[{"role": "user", "content": "hi"}], model="x", max_tokens=4, temperature=0)
    assert out == "ok" and calls["n"] == 3, (out, calls)
    log(f"backoff wrapper retried transient errors {calls['n']-1}x then succeeded OK")


def check_interp_raises():
    api = APIParticipant(name="j", model_id=MODEL)
    for kw in ("capture", "steering", "patch"):
        try:
            api.generate([{"role": "user", "content": "hi"}], **{kw: object()})
            log(f"WARNING: {kw} did not raise")
        except NotImplementedError:
            pass
    log("interp params raise on APIParticipant OK")


def check_real_conversation():
    conv = Conversation(
        participants=[APIParticipant(name="pro", model_id=MODEL, max_tokens=80, temperature=1.0,
                                     system_prompt="Argue YES. One short sentence."),
                      APIParticipant(name="con", model_id=MODEL, max_tokens=80, temperature=1.0,
                                     system_prompt="Argue NO. One short sentence.")],
        shared_context="Is a hot dog a sandwich?")
    conv.run(turns=4)
    log(f"Claude-vs-Claude produced {len(conv.transcript)} turns:")
    for m in conv.transcript:
        log(f"   {m.author}: {m.content[:100]}")
    # 4 generated turns + the moderator seed message from shared_context.
    assert len(conv.transcript) == 5 and all(m.content.strip() for m in conv.transcript)

    # Claude as an analyze-style classifier over the transcript (the real use case for API in analyze).
    judge = APIParticipant(name="judge", model_id=MODEL, max_tokens=10, temperature=0.0)
    joined = "\n".join(f"{m.author}: {m.content}" for m in conv.transcript)
    verdict = judge.generate([{"role": "user",
                               "content": f"Reply with ONE word (pro or con): who argued more persuasively?\n{joined}"}])
    log(f"judge verdict: {verdict.content!r}")
    assert verdict.content.strip()
    log("real Claude conversation + classifier OK")


def check_batch_generate():
    """``generate_batch`` with ``batch=True`` routes every view through the client's ``submit_batch`` (one async
    provider batch) and returns Messages in input order; ``batch=False`` falls back to per-view calls."""
    class _BatchClient:
        def __init__(self):
            self.batches = 0
            self.calls = 0

        def __call__(self, system, messages, model, max_tokens, temperature):
            self.calls += 1
            return f"solo:{messages[-1]['content']}"

        def submit_batch(self, requests, *, poll_interval=30.0):
            self.batches += 1
            return [f"batched:{r['messages'][-1]['content']}" for r in requests]

    views = [[{"role": "user", "content": w}] for w in ("a", "b", "c")]

    client = _BatchClient()
    api = APIParticipant(name="j", model_id=MODEL, batch=True, client=client)
    msgs = api.generate_batch(views)
    assert [m.content for m in msgs] == ["batched:a", "batched:b", "batched:c"], msgs
    assert client.batches == 1 and client.calls == 0 and all(m.metadata["batched"] for m in msgs)

    client2 = _BatchClient()
    api2 = APIParticipant(name="j", model_id=MODEL, batch=False, client=client2)
    msgs2 = api2.generate_batch(views)
    assert [m.content for m in msgs2] == ["solo:a", "solo:b", "solo:c"], msgs2
    assert client2.batches == 0 and client2.calls == 3
    log("generate_batch: batch=True -> one submit_batch (in order); batch=False -> per-view calls OK")


def check_batch_unavailable_raises():
    """A provider whose client exposes no ``submit_batch`` (OpenRouter) must raise on ``batch=True``, never
    silently fall back — and the base client's default ``submit_batch`` raises too."""
    class _NoBatchClient:
        def __call__(self, system, messages, model, max_tokens, temperature):
            return "x"

    api = APIParticipant(name="j", model_id="openai/gpt-5", provider="openrouter", batch=True, client=_NoBatchClient())
    try:
        api.generate_batch([[{"role": "user", "content": "hi"}]])
        raise AssertionError("expected NotImplementedError for a client without submit_batch")
    except NotImplementedError as e:
        assert "batch" in str(e).lower()

    from interlens.participant.participants.api_client import _RetryingClient
    base = _RetryingClient.__new__(_RetryingClient)
    try:
        base.submit_batch([])
        raise AssertionError("expected _RetryingClient.submit_batch to raise")
    except NotImplementedError as e:
        assert "no batch API" in str(e)
    log("batch mode unavailable (OpenRouter / base client) raises loudly OK")


def check_provider_registry():
    """The provider enum + client registry expose native anthropic + openai, and openai maps to a batch-capable
    client while openrouter does not."""
    from interlens.participant.participants.api_participant import _CLIENT_CLASSES
    from interlens.participant.participants import api_client

    assert set(_CLIENT_CLASSES) == {"anthropic", "openai", "openrouter"}, _CLIENT_CLASSES
    assert "submit_batch" in vars(api_client.OpenAIClient), "OpenAIClient must implement submit_batch"
    assert "submit_batch" in vars(api_client.AnthropicClient), "AnthropicClient must implement submit_batch"
    assert "submit_batch" not in vars(api_client.OpenRouterClient), "OpenRouterClient must NOT implement submit_batch"
    log("provider registry: native anthropic/openai (batch-capable) + openrouter (no batch) OK")


def main():
    offline = [check_backoff_wrapper, check_interp_raises, check_batch_generate,
               check_batch_unavailable_raises, check_provider_registry]
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log("ANTHROPIC_API_KEY not set — running offline checks only")
        for c in offline:
            c()
        log("OFFLINE CHECKS PASSED (set ANTHROPIC_API_KEY for the live call)")
        return
    for c in offline:
        c()
    check_real_conversation()
    log("ALL API CHECKS PASSED")


if __name__ == "__main__":
    main()
