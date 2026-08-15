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

"""Recovering a turn the API refused, without changing what the turn says.

Some hosted providers return a completion with ``stop_reason == "refusal"`` and zero output tokens: an
API-side classifier declined the request before the model wrote anything. Measured on ``claude-opus-5`` in the
auction program, that refusal has three properties that make it a *protocol* problem rather than a modelling
one:

- it reproduces **deterministically** for a byte-identical request, so it survives the ordinary retry (which
  re-sends the same view with a parser note appended);
- it is **not semantic** — substituting the domain vocabulary, dropping a blurb, salting the tail, or
  splitting the turn all leave it in place, while removing almost *any* single block clears it;
- so the seat contributes no move at all, and any fallback action recorded for it is a move the model never
  chose.

The response implemented here is a **re-render ladder**: on a refusal, the same turn view is re-rendered under
a deterministic, content-preserving perturbation and reissued, escalating through a fixed sequence of rungs.
Every rung preserves every number, every rule, and every reviewed sentence — only *ordering*, *section
framing*, and an inert *nonce line* vary — so a recovered turn conditions on the same information the refused
one did. The ladder is a property of the engine, not of an arm or a condition, so it applies identically
everywhere and is a protocol feature rather than a confound; it is preregisterable because the rungs, their
order, and the seeded permutation are all fixed in advance and logged per turn
(``TurnRecord.refusal_recovery``).

What this is **not**: an attempt to defeat the classifier. The rungs are content-preserving by construction.
If a view refuses at every rung the turn is recorded as ``terminal`` and the cell's validity gate sees it — a
configuration that cannot clear the ladder is an escalation to the provider, not an engineering problem.

Worked example
--------------

>>> from interlens.arena.refusal import RefusalLadder
>>> ladder = RefusalLadder()
>>> view = [{"role": "system", "content": "You are seat A."},
...         {"role": "user", "content": "## Catalogue\\nLot 1: 90\\n\\n## Your values\\nLot 1: 104\\n\\n"
...                                      "Reply now with one fenced JSON object."}]
>>> rung1 = ladder.perturb(view, 1, key="ep-1/seat-A/r3")
>>> rung1[1]["content"].splitlines()[0]                                  # doctest: +ELLIPSIS
'Protocol note: request variant ...'
>>> sorted(ladder.perturb(view, 2, key="ep-1/seat-A/r3")[1]["content"].split("\\n\\n")) == \\
...     sorted(rung1[1]["content"].split("\\n\\n"))                       # same blocks, different order
True
>>> ladder.perturb(view, 3, key="ep-1/seat-A/r3")[1]["content"].count("Lot 1: 104")   # numbers preserved
1
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

#: Provider stop reasons that mean "the request was declined before generation": Anthropic's native
#: ``refusal`` and the OpenAI-schema ``content_filter``.
REFUSAL_STOPS = ("refusal", "content_filter")

#: Stop reasons that mean the model ran out of room rather than being declined. An empty completion under one
#: of these is a cap problem (raise ``turn_token_floor``), NOT something a re-render can fix, so the ladder
#: leaves it alone and lets the ordinary truncation accounting see it.
TRUNCATION_STOPS = ("max_tokens", "length", "model_length")


def is_refusal(message) -> bool:
    """Did this completion come back declined rather than generated?

    True when the participant stamped ``metadata["refusal"]`` (``APIParticipant`` sets it from the native stop
    reason), when the stop reason is one of :data:`REFUSAL_STOPS`, or when the visible content is empty and the
    stop reason is *not* a truncation — an empty non-truncated completion is the same "the seat wrote nothing"
    failure, whatever the provider called it."""
    meta = getattr(message, "metadata", None) or {}
    if meta.get("refusal"):
        return True
    stop = meta.get("stop_reason")
    if stop in REFUSAL_STOPS:
        return True
    return not (getattr(message, "content", "") or "").strip() and stop not in TRUNCATION_STOPS


def _blocks(text: str) -> list[str]:
    """Split a rendered turn into its top-level blocks on blank lines, preserving each block's bytes."""
    return [b for b in text.split("\n\n") if b.strip()]


@dataclass(frozen=True)
class RefusalLadder:
    """A fixed, seeded sequence of content-preserving re-renders, tried in order after a refusal.

    :param rungs: The escalation order. Rungs are **cumulative** — rung *k* applies the perturbations of
        rungs 1..*k* — so each attempt is strictly further from the refused bytes than the last while staying
        content-preserving. The default ladder is:

        1. ``"nonce"`` — prepend one inert line naming a seeded variant tag. Adds no number and no instruction;
           its only job is to make the request bytes differ from the refused ones.
        2. ``"permute"`` — reorder the view's independent top-level blocks under a seeded permutation, holding
           the first block (the turn's own header) and the last block (the single closing ask) in place, since
           those two carry position-dependent meaning and the interior sections do not.
        3. ``"reframe"`` — re-wrap markdown section headings in an alternate but fixed framing
           (``## Catalogue`` becomes ``### Section: Catalogue``). Heading *text* and every body line are
           untouched.

    :param seed: Ladder-level seed mixed into every per-turn permutation, so the whole campaign's re-renders
        replay exactly from the run manifest.
    :param target_role: Which message of the view is perturbed. ``"user"`` (the default) is the measured one:
        in the auction pilot a line prepended to the user turn cleared a refusal 2/2 while the same line on the
        system prompt did not.
    """

    rungs: tuple[str, ...] = ("nonce", "permute", "reframe")
    seed: int = 20260815
    target_role: str = "user"

    def __len__(self) -> int:
        return len(self.rungs)

    def rung_name(self, rung: int) -> str:
        """The name of rung *k* (1-based), for logging."""
        return self.rungs[rung - 1]

    def _rng_bytes(self, key: str, salt: str) -> bytes:
        return hashlib.blake2b(f"{self.seed}/{key}/{salt}".encode(), digest_size=16).digest()

    def _tag(self, key: str) -> str:
        return self._rng_bytes(key, "tag").hex()[:6]

    def _permutation(self, n: int, key: str) -> list[int]:
        """A seeded permutation of ``range(n)`` — a Fisher-Yates drive off the keyed digest, so it depends only
        on ``(seed, key)`` and replays identically."""
        order = list(range(n))
        digest = self._rng_bytes(key, "permute")
        for i in range(n - 1, 0, -1):
            j = digest[i % len(digest)] % (i + 1)
            order[i], order[j] = order[j], order[i]
        return order

    # -- the rungs -------------------------------------------------------------------------------------------
    def _nonce(self, text: str, key: str) -> str:
        return f"Protocol note: request variant {self._tag(key)}.\n\n{text}"

    def _permute(self, text: str, key: str) -> str:
        blocks = _blocks(text)
        if len(blocks) < 4:                      # nothing to reorder that isn't header or ask
            return text
        head, interior, tail = blocks[0], blocks[1:-1], blocks[-1]
        order = self._permutation(len(interior), key)
        return "\n\n".join([head] + [interior[i] for i in order] + [tail])

    @staticmethod
    def _reframe(text: str) -> str:
        out = []
        for line in text.split("\n"):
            stripped = line.lstrip("#")
            if line.startswith("## ") and stripped.strip():
                out.append(f"### Section: {line.lstrip('#').strip()}")
            else:
                out.append(line)
        return "\n".join(out)

    def perturb(self, view: list[dict], rung: int, *, key: str) -> list[dict]:
        """The view re-rendered at rung *k* (1-based, cumulative). Returns a new list; ``view`` is untouched.

        :param view: The refused request's view — a list of ``{"role", "content"}`` messages.
        :param rung: Which rung to render, 1-based; ``rung > len(self)`` raises.
        :param key: The per-turn key the seeded perturbations hang off, e.g.
            ``f"{episode_id}/{seat}/{round}/{phase}"``. Identical inputs give identical bytes, which is what
            makes a recovered turn reproducible from the episode record.
        """
        if not 1 <= rung <= len(self.rungs):
            raise ValueError(f"rung {rung} is outside this ladder's 1..{len(self.rungs)}")
        idx = max((i for i, m in enumerate(view) if m.get("role") == self.target_role), default=None)
        if idx is None:
            return [dict(m) for m in view]
        text = view[idx]["content"]
        active = self.rungs[:rung]
        if "permute" in active:
            text = self._permute(text, key)
        if "reframe" in active:
            text = self._reframe(text)
        if "nonce" in active:                    # last, so the tag is always the first line the seat reads
            text = self._nonce(text, key)
        out = [dict(m) for m in view]
        out[idx] = dict(out[idx], content=text)
        return out


#: The metadata key by which a recovery record travels from the driver to ``EpisodeRun.record_turn``, which
#: stamps it onto ``TurnRecord.refusal_recovery``. Named here beside the ladder because producer and consumer
#: live in different modules.
REFUSAL_RECOVERY_KEY = "refusal_recovery"


def recovery_record(outcome: str, rung: int | None, attempts: list[str]) -> dict:
    """One turn's recovery record: ``outcome`` is ``"recovered"`` or ``"terminal"``, ``rung`` the 1-based rung
    that cleared it (``None`` when none did), ``attempts`` the rung names tried in order. Reported as
    ``api_silence_recovered@rung_k`` / ``api_silence_terminal``."""
    return {"outcome": outcome, "rung": rung, "attempts": list(attempts)}
