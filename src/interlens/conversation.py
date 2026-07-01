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

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import torch

from .participant import Participant
from .message import Message
from .transcript import Transcript
from .view import ViewSegment
from .reasoning_visibility import ReasoningVisibility
from .execution_mode import ExecutionMode
from .context import ContextPolicy, ErrorPolicy
from .stop import StopCondition, AnyStopCondition
from .interp.activation_cache import ActivationCache, CaptureSpec, OffloadLocation
from .interp.capture import CaptureRequest
from .hooks.message_hook import HookAction

if TYPE_CHECKING:
	from .factories import ModelLike

# A reference to one participant: the ``Participant`` object, its ``name`` (str), or its index (int).
ParticipantLike = Participant | str | int
# An opening/injected turn: a ready ``Message`` (explicit author), a ``str`` (attributed to the LAST participant
# so the first speaker replies to it), or ``None`` (append nothing).
PromptLike = Message | str | None


@dataclass
class Conversation:
	"""Orchestrates turn-taking between participants over a shared, perspective-neutral ``Transcript``.

	``Conversation`` owns *who speaks when* and the **ordered view pipeline**: for each speaker it assembles a
	structured, typed view (system block → private context → transcript turns), fits it to the context window on
	those typed segments, then lets the participant flatten it (family fold/merge) and generate. Keeping the
	pipeline ordered — fit *before* the lossy family flatten — is what lets the context policy preserve the
	system/moderator framing reliably (see ``context/``).

	Scenario framing is split by ownership: *shared* framing (``shared_context`` as a moderator seed turn,
	``shared_system_prompt``) lives here; *private* framing (``system_prompt``, ``private_context``) lives on
	each participant, so it is naturally invisible to the others and to the transcript.
	"""

	participants: tuple[Participant, ...]
	"""The conversation's participants. **Order is significant — it is the default speaking order.** ``run``
	alternates through them in this order (turn ``k`` is ``participants[(start + k) % n]``), and ``run(first=...)``
	only shifts the starting index; so the first element speaks first unless ``first`` overrides. Names must be
	unique and none may equal ``moderator_name``."""

	transcript: Transcript = field(default_factory=Transcript)
	"""The shared, perspective-neutral message history. Defaults to empty; when starting fresh, ``shared_context``
	is seeded as the first ``moderator_name`` turn (a branched/loaded transcript already contains it and is not
	re-seeded)."""

	shared_context: str | None = None
	"""Scenario framing every participant sees, injected once as a leading ``moderator_name`` turn when the
	transcript starts empty. ``None`` = no seed turn."""

	shared_system_prompt: str | None = None
	"""A system prompt merged into every participant's system block (after that participant's private
	``system_prompt``). ``None`` = no shared system prompt."""

	moderator_name: str = "moderator"
	"""Author name used for the ``shared_context`` seed and any moderator turns. Must not collide with a
	participant name (validated in ``__post_init__``)."""

	context_policy: ContextPolicy = field(default_factory=ErrorPolicy)
	"""How each speaker's view is fit to the context window — run on the typed segments *before* the family
	flatten so framing is preserved. Default ``ErrorPolicy`` raises on overflow rather than silently truncating;
	see ``context/`` for sliding-window / drop-oldest / summarize alternatives."""

	context_limit: int | None = None
	"""Token budget the ``context_policy`` fits to. ``None`` = use the tokenizer's own ``model_max_length``."""

	reasoning_visibility: ReasoningVisibility = ReasoningVisibility.STRIP
	"""Whether a prior turn's parsed ``<think>`` reasoning is re-injected into later views: ``STRIP`` (never),
	``SELF_RETAIN`` (a speaker sees only its own), ``SHARED`` (everyone sees everyone's). Reasoning is always
	parsed into ``metadata['parsed_think']`` regardless, so interp is unaffected."""

	execution_mode: ExecutionMode = ExecutionMode.THROUGHPUT
	"""The determinism-vs-throughput tension the runner consults: ``THROUGHPUT`` (default) permits batched
	co-stepping + KV reuse + flash-attn (only *distributional* reproducibility); ``DETERMINISTIC`` disables those
	for token-identical replay and interp fidelity."""

	message_hooks: list = field(default_factory=list)
	"""Runtime-only middleware (**not** serialized into the template): each hook vets / edits / denies a freshly
	generated message before it is committed. Applied in order; default empty = pass-through. See ``hooks/``."""

	def __post_init__(self):
		self.participants = tuple(self.participants)
		names = [p.name for p in self.participants]
		if len(names) != len(set(names)):
			raise ValueError(f"participant names must be unique, got {names}")
		if self.moderator_name in names:
			raise ValueError(f"moderator_name {self.moderator_name!r} collides with a participant name")
		self.by_name = {p.name: p for p in self.participants}
		self._pending_capture: CaptureRequest | None = None
		# Seed the shared scenario as a moderator turn — but only when starting fresh, so a branched/loaded
		# conversation (whose transcript already contains the seed) is not re-seeded.
		if self.shared_context and len(self.transcript) == 0:
			self.transcript.append(self.moderator_name, self.shared_context)

	@classmethod
	def from_models(cls, models: tuple[ModelLike, ...], names: tuple[str, ...] = ("a", "b"),
	                device: str | torch.device = "cuda", dtype: torch.dtype = torch.bfloat16,
	                shared_context: str | None = None, shared_system_prompt: str | None = None,
	                prompt: PromptLike = None, **gen_kwargs) -> "Conversation":
		"""Scaffold a conversation directly from a tuple of ``models`` — each an HF id or an already-loaded
		``PreTrainedModel`` (see ``ModelLike``). Convenience wrapper around
		``factories.conversation_from_models``; each model becomes a family-correct participant and ``names`` gives
		them identities. **The order of ``models`` / ``names`` is the speaking order** — the first speaks first
		unless you pass ``first=`` to ``run``. ``**gen_kwargs`` are forwarded to every participant.

		Scenario framing is available here too: ``shared_system_prompt`` (instructions, system role) and
		``shared_context`` (a neutral ``moderator``-voiced opening seen by everyone). ``prompt`` is a separate
		convenience for a *participant*-voiced opener (a ``str`` is attributed to the last participant). See that
		function for the details."""
		from .factories import conversation_from_models  # lazy: factories imports this module

		return conversation_from_models(models, names=names, device=device, dtype=dtype,
		                                shared_context=shared_context, shared_system_prompt=shared_system_prompt,
		                                prompt=prompt, **gen_kwargs)

	# --- view pipeline -------------------------------------------------------------------------------------

	def _system_text(self, participant: Participant) -> str | None:
		"""Merge a participant's private ``system_prompt`` (first) with the ``shared_system_prompt`` into one
		leading system block, for chat templates that permit only a single system message."""
		parts = [t for t in (participant.system_prompt, self.shared_system_prompt) if t]
		return "\n\n".join(parts) if parts else None

	def _reasoning_for(self, participant: Participant, message: Message) -> str | None:
		"""Per ``ReasoningVisibility``, decide whether a prior turn's parsed reasoning is re-injected into
		``participant``'s view (STRIP: never; SELF_RETAIN: only its own; SHARED: everyone's)."""
		think = message.metadata.get("parsed_think")
		if not think or self.reasoning_visibility == ReasoningVisibility.STRIP:
			return None
		if self.reasoning_visibility == ReasoningVisibility.SHARED:
			return think
		if self.reasoning_visibility == ReasoningVisibility.SELF_RETAIN and message.author == participant.name:
			return think
		return None

	def _assemble_segments(self, participant: Participant, extra=()) -> list[ViewSegment]:
		"""Build the structured, typed view for ``participant``: system block, then private context, then the
		transcript (+ optional ephemeral ``extra`` messages) role-swapped to this participant's perspective."""
		segments: list[ViewSegment] = []

		system_text = self._system_text(participant)
		if system_text:
			segments.append(ViewSegment(role="system", content=system_text, origin="system"))

		for item in participant.private_context:
			segments.append(ViewSegment(role=item.role_hint, content=item.content,
			                            origin="private_context", author=item.author))

		for message in (*self.transcript, *extra):
			role = participant.self_role if message.author == participant.name else participant.others_role
			origin = "moderator" if message.author == self.moderator_name else "turn"
			content = message.content
			reasoning = self._reasoning_for(participant, message)
			if reasoning:
				content = f"<reasoning>\n{reasoning}\n</reasoning>\n{content}"
			segments.append(ViewSegment(role=role, content=content, origin=origin, author=message.author))

		return segments

	def _view(self, participant: Participant, extra=()) -> list[dict]:
		"""Run the full pipeline: assemble typed segments → context-fit (on segments, pre-flatten) → family
		flatten. Returns the ``[{role, content}]`` list ready for the participant's chat template."""
		segments = self._assemble_segments(participant, extra)
		tokenizer = getattr(participant, "tokenizer", None)
		if tokenizer is not None:
			segments = self.context_policy.fit(segments, tokenizer, self.context_limit)
		return participant.finalize_view(segments)

	# --- turn-taking ---------------------------------------------------------------------------------------

	def step(self, speaker: Participant, *, steering=None, capture=None, patch=None,
	         return_logprobs: bool = False, max_new_tokens: int | None = None) -> Message:
		"""Have ``speaker`` produce and commit one turn. Interp options flow to ``generate``; if no ``capture`` is
		passed but a ``conv.capture(...)`` block is active, its pending request is used (auto-tagged by turn)."""
		if capture is None:
			capture = self._pending_capture
		turn = len(self.transcript)
		message = speaker.generate(self._view(speaker), steering=steering, capture=capture,
		                           patch=patch, return_logprobs=return_logprobs, turn=turn,
		                           max_new_tokens=max_new_tokens)
		message = self._apply_hooks(message)
		if message is None:
			return None  # a hook denied this turn; nothing is committed
		self.transcript.messages.append(message)
		return message

	def _apply_hooks(self, message):
		"""Pass a freshly generated message through the hook chain before it is committed. DENY drops the turn
		(returns None); EDIT substitutes the replacement; APPROVE (and an empty chain) leaves it unchanged."""
		for hook in self.message_hooks:
			result = hook.review(message, self)
			if result.action == HookAction.DENY:
				return None
			if result.action == HookAction.EDIT:
				message = result.message
		return message

	@contextmanager
	def capture(self, sites=("residual",), layers=None, offload: OffloadLocation = "cpu"):
		"""Context manager that captures activations for every ``step`` inside the block into a fresh
		``ActivationCache``, auto-tagged by the current speaker + turn::

			with conv.capture(sites=["residual"], layers=[8, 12]) as cache:
				conv.step(bob)
			cache.at(participant="bob", layer=12)
		"""
		cache = ActivationCache(offload=offload)
		spec = CaptureSpec(sites=tuple(sites), layers=tuple(layers) if layers is not None else None, offload=offload)
		self._pending_capture = CaptureRequest(cache=cache, spec=spec)
		try:
			yield cache
		finally:
			self._pending_capture = None

	def run(self, turns: int | None = None, until: StopCondition | list | None = None,
	        first: ParticipantLike | None = None, prompt: PromptLike = None) -> Transcript:
		"""Alternate speakers until ``turns`` elapse and/or a ``StopCondition`` fires (whichever comes first).

		Speakers are taken in ``participants`` order (that tuple's order IS the turn order); ``first`` sets who
		starts (default: ``participants[0]``) and the rest follow round-robin. ``first`` may be a ``Participant``,
		its ``name`` (str), or its index (int) — resolved via ``_parse_participant`` (raises if it isn't in this
		conversation). ``until`` may be a single condition or a list (any of which stops the run). Stop conditions
		are ``reset()`` at the start so a reused condition doesn't leak state across runs.

		``prompt`` (optional) is appended to the transcript **before** the run — a convenience so you don't have to
		touch ``transcript`` by hand: a ``str`` is attributed to the LAST participant (so the ``first`` speaker
		naturally replies to it), a ``Message`` is appended as-is, ``None`` appends nothing. It always appends to
		the *current end* of the transcript; on a non-empty transcript it is simply one more trailing turn (it does
		not reset or reseed anything).
		"""
		if turns is None and until is None:
			raise ValueError("run requires at least one of `turns` or `until`")
		self._append_prompt(prompt)
		stop = self._as_stop(until)
		if stop is not None:
			stop.reset()

		start = self._parse_participant(first) if first is not None else 0
		n = len(self.participants)
		i = 0
		while turns is None or i < turns:
			message = self.step(self.participants[(start + i) % n])
			i += 1
			# A hook may have denied the turn (message is None); only a committed message is checked for stopping.
			if message is not None and stop is not None and stop.should_stop(self, message):
				break
		return self.transcript
	
	def _append_prompt(self, prompt: PromptLike) -> None:
		"""Append an opening/injected turn to the transcript (see ``PromptLike``): a ``str`` becomes a turn by the
		LAST participant, a ``Message`` is appended verbatim, ``None`` is a no-op. Always appends to the current
		end — it never resets or reseeds an existing transcript."""
		if prompt is None:
			return
		if isinstance(prompt, Message):
			self.transcript.messages.append(prompt)
		elif isinstance(prompt, str):
			if not self.participants:
				raise ValueError("cannot append a str prompt to a conversation with no participants")
			self.transcript.append(self.participants[-1].name, prompt)
		else:
			raise TypeError(f"prompt must be a str, Message, or None, got {type(prompt).__name__}")

	def _parse_participant(self, participant: ParticipantLike) -> int:
		"""Resolves a participant from a participant object, name, or index. Raises an error if that participant does not exist in this Conversation. Returns the index of the participant within self.participants."""
		if isinstance(participant, Participant):
			try:
				return self.participants.index(participant)
			except ValueError:
				raise ValueError(f"Participant {participant.name} is not in this Conversation.")
		elif isinstance(participant, str):
			for idx, p in enumerate(self.participants):
				if p.name == participant:
					return idx
			raise ValueError(f"Participant with name '{participant}' is not in this Conversation.")
		elif isinstance(participant, int):
			if 0 <= participant < len(self.participants):
				return participant
			else:
				raise IndexError(f"Participant index {participant} is out of range for this Conversation.")
		else:
			raise TypeError("Participant must be a Participant object, name (str), or index (int).")

	@staticmethod
	def _as_stop(until) -> StopCondition | None:
		if until is None:
			return None
		if isinstance(until, StopCondition):
			return until
		return AnyStopCondition(list(until))

	# --- branching & ephemeral sampling --------------------------------------------------------------------

	def branch(self) -> "Conversation":
		"""Fork into a new ``Conversation`` that **reuses the same participant objects** (shared weights, zero
		GPU cost) with a copied transcript. The branch can diverge freely; the original is untouched."""
		return Conversation(
			participants=self.participants,
			transcript=self.transcript.copy(),
			shared_context=self.shared_context,
			shared_system_prompt=self.shared_system_prompt,
			moderator_name=self.moderator_name,
			context_policy=self.context_policy,
			context_limit=self.context_limit,
			reasoning_visibility=self.reasoning_visibility,
			execution_mode=self.execution_mode,
			message_hooks=list(self.message_hooks),
		)

	def sample(self, speaker: Participant | str, message: str | None = None, *,
	           as_author: str | None = None, steering=None, capture=None, patch=None,
	           return_logprobs: bool = False, max_new_tokens: int | None = None) -> Message:
		"""Ephemerally sample ``speaker``'s response to an optional temporary ``message`` **without mutating the
		transcript**. Pure read of current state: safe to call repeatedly / in a loop. ``message`` is attributed
		to ``as_author`` (default: the other participant), so it reads as a normal incoming turn. The same interp
		options as ``step`` are honored on the ephemeral generation."""
		speaker = self.by_name[speaker] if isinstance(speaker, str) else speaker
		extra = []
		if message is not None:
			author = as_author or self._default_other(speaker)
			extra = [Message(author=author, content=message)]
		return speaker.generate(self._view(speaker, extra=extra), steering=steering, capture=capture,
		                        patch=patch, return_logprobs=return_logprobs, turn=len(self.transcript),
		                        max_new_tokens=max_new_tokens)

	def _default_other(self, speaker: Participant) -> str:
		"""The natural author for an injected sample message: some other participant, else the moderator."""
		for p in self.participants:
			if p.name != speaker.name:
				return p.name
		return self.moderator_name

	# --- serialization (levels 2 & 3) ----------------------------------------------------------------------

	def to_template(self):
		"""Extract the reusable ``ConversationTemplate`` (specs + scenario framing, no messages) from this live
		conversation, by asking each participant for its config."""
		from .template import ConversationTemplate

		return ConversationTemplate(
			participants=[p.to_config() for p in self.participants],
			shared_context=self.shared_context,
			shared_system_prompt=self.shared_system_prompt,
			moderator_name=self.moderator_name,
			context_policy=self.context_policy,
			context_limit=self.context_limit,
			reasoning_visibility=self.reasoning_visibility,
			execution_mode=self.execution_mode,
		)

	def save(self, directory) -> None:
		"""Persist the entire conversation (level 3): the template + the transcript, side by side."""
		from pathlib import Path

		directory = Path(directory)
		directory.mkdir(parents=True, exist_ok=True)
		self.to_template().save(directory / "template.json")
		self.transcript.save(directory / "transcript.json")

	@classmethod
	def load(cls, directory, devices="cuda") -> "Conversation":
		"""Rebuild a saved conversation: reload participants from the template and **attach** the saved
		transcript, resuming from that state. This does NOT regenerate messages — use ``replay`` for that."""
		from pathlib import Path
		from .template import ConversationTemplate
		from .transcript import Transcript

		directory = Path(directory)
		template = ConversationTemplate.load(directory / "template.json")
		transcript = Transcript.load(directory / "transcript.json")
		return template.build(devices, transcript=transcript)

	def replay(self, devices="cuda") -> "Conversation":
		"""Deterministically **regenerate** the conversation from its template, re-running each model turn in the
		recorded author order. Token-identical only in ``ExecutionMode.DETERMINISTIC`` (throughput mode is
		distributional); meaningful for fully model-generated transcripts."""
		fresh = self.to_template().build(devices)
		# Skip the moderator seed (it's re-created by build from shared_context); regenerate the rest in order.
		for message in self.transcript:
			if message.author == self.moderator_name:
				continue
			speaker = fresh.by_name.get(message.author)
			if speaker is not None:
				fresh.step(speaker)
		return fresh
