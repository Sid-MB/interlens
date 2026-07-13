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

from __future__ import annotations

from ..participant import Participant
from ...message import Message


class ScriptedParticipant(Participant):
    """A non-model participant that replies with **pre-written (scripted) messages**, cycled in order — its turns
    are fixed, NOT generated from the conversation.

    The motivating use is a **reliable adversary / pusher**: to measure whether a target model capitulates under
    social pressure you need an interlocutor that asserts a specific (often wrong) answer *every* turn. A real
    model is a poor adversary for this — aligned/reasoning models frequently refuse to argue a known-wrong answer
    and instead re-solve correctly, so the "pressure" silently vanishes (an invisible confound unless you read
    transcripts). Scripting the adversary guarantees uniform, controlled pressure and costs no model/API calls.

    It ignores the conversation ``view`` (its replies are fixed) and holds no activations, so it raises on any
    interp request (``steering``/``capture``/``patch``/``return_logprobs``) rather than silently ignoring it —
    consistent with the ``Participant.generate`` contract.

    Parameters
    ----------
    name : str
        Identifier within the conversation.
    scripts : str | list[str]
        The canned message(s). A single string is treated as a one-element list. Turns cycle through the list in
        order (turn ``k`` emits ``scripts[k % len(scripts)]``), so a few varied assertions read less robotically
        than one repeated line while still asserting the same position.
    system_prompt : str | None
        Optional system framing (recorded for view/transcript symmetry; the scripted replies don't depend on it).
    private_context : tuple
        Optional private context, for parity with other participants (unused by the fixed replies).
    """

    self_role = "assistant"
    others_role = "user"

    def __init__(self, name: str, scripts: "str | list[str]", *, system_prompt: str | None = None,
                 private_context: tuple = ()):
        self.name = name
        self.scripts = [scripts] if isinstance(scripts, str) else list(scripts)
        if not self.scripts:
            raise ValueError("ScriptedParticipant needs at least one scripted message")
        self.system_prompt = system_prompt
        self.private_context = tuple(private_context)
        self._turn = 0

    def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
                 return_logprobs: bool = False, turn: int | None = None,
                 max_new_tokens: int | None = None) -> Message:
        """Return the next scripted message (cycled), ignoring ``view``. Raises on interp requests — a scripted
        participant has no model/activations to steer, capture, patch, or read logprobs from."""
        if steering is not None or capture is not None or patch is not None or return_logprobs:
            raise NotImplementedError(
                f"ScriptedParticipant {self.name!r} has no model: steering/capture/patch/logprobs are unavailable")
        content = self.scripts[self._turn % len(self.scripts)]
        self._turn += 1
        return Message(author=self.name, content=content)
