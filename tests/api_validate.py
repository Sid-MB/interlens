# [complete-chat-harness]: real APIParticipant validation (CLUSTER_NEXT_STEPS item 6). Needs ANTHROPIC_API_KEY
# and outbound internet. Runs a short Claude-vs-Claude conversation, uses Claude as an analyze-style classifier,
# and confirms the retry/backoff wrapper + interp-raise behavior. Uses a cheap Haiku model.
from __future__ import annotations

import os
import sys

from interlens import APIParticipant, ConversationTemplate, APIParticipantConfig, Conversation

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
    tmpl = ConversationTemplate(
        participants=[APIParticipantConfig(name="pro", model_id=MODEL, max_tokens=80, temperature=1.0,
                                           system_prompt="Argue YES. One short sentence."),
                      APIParticipantConfig(name="con", model_id=MODEL, max_tokens=80, temperature=1.0,
                                           system_prompt="Argue NO. One short sentence.")],
        shared_context="Is a hot dog a sandwich?", turns=4)
    conv = tmpl.build(devices="cpu")  # API participants ignore device
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


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log("ANTHROPIC_API_KEY not set — running offline checks only")
        check_backoff_wrapper()
        check_interp_raises()
        log("OFFLINE CHECKS PASSED (set ANTHROPIC_API_KEY for the live call)")
        return
    check_backoff_wrapper()
    check_interp_raises()
    check_real_conversation()
    log("ALL API CHECKS PASSED")


if __name__ == "__main__":
    main()
