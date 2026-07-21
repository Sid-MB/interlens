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
from typing import TYPE_CHECKING, overload

import torch

from .participant import Participant
from .functional import Functional, sugar_fields
from .message import Message
from .transcript import Transcript, MessageRef
from .templating import has_fields, resolve
from .view import ViewSegment
from .reasoning_visibility import ReasoningVisibility
from .execution_mode import ExecutionMode
from .context import ContextPolicy, ErrorPolicy
from .stop import StopCondition, AnyStopCondition, active_stop_conditions
from .interp.activation_cache import ActivationCache, CaptureSpec, OffloadLocation
from .interp.capture import CaptureRequest
from .hooks.message_hook import HookAction

if TYPE_CHECKING:
	from .factories import ModelLike
	from .runner import RunReport

# A reference to one participant: the ``Participant`` object, its ``name`` (str), or its index (int).
ParticipantLike = Participant | str | int
# An opening/injected turn: a ready ``Message`` (explicit author), a ``str`` (attributed to the LAST participant
# so the first speaker replies to it), or ``None`` (append nothing).
PromptLike = Message | str | None


@sugar_fields("turns", "data", "analyzer", "name", "seed", "run_until")
@dataclass
class Conversation(Functional):
	"""A multi-agent conversation: the recipe, the live dialogue, AND the benchmark-rollout driver, all in one
	lightweight object.

	It orchestrates turn-taking between ``Participant``s over a shared, perspective-neutral ``Transcript``, owning
	*who speaks when* and the **ordered view pipeline**: for each speaker it assembles a structured, typed view
	(system block → private context → transcript turns), fits it to the context window on those typed segments,
	then lets the participant flatten it (family fold/merge) and generate. Fitting *before* the lossy family
	flatten is what lets the context policy preserve the system/moderator framing reliably (see ``context/``).

	Scenario framing is split by ownership: *shared* framing (``shared_context`` as a moderator seed turn,
	``shared_system_prompt``) lives here; *private* framing (``system_prompt``, ``private_context``) lives on each
	participant, so it is naturally invisible to the others and to the transcript.

	**Copy-on-write + lazy.** Participants load their weights lazily, so an unrun ``Conversation`` is a cheap
	recipe. Build it up functionally — ``conv.turns(4).data(ds).analyzer(grade)`` — where each dot-modifier
	returns a modified *copy* (via ``Functional.set``), never mutating the original; call ``.set(field=value)`` for
	fields without a dot-modifier. ``build``-free: run it directly with ``run()``, or expand it over data / N
	samples with ``rollout()`` (which copies it per row — see there).

	Also supports branching (``branch()`` / ``branch_from()``), in-place history editing (``rewind()``, ``edit()``,
	``reset()``), ephemeral sampling (``sample()`` / ``sample_all()``), activation capture (``capture()``), and
	disk persistence (``save()`` / ``load()``).
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
	transcript starts empty. ``None`` = no seed turn; ``""`` still seeds a (blank) turn, so the first speaker has
	a non-empty view."""

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
	"""Runtime-only middleware (**not** persisted): each hook vets / edits / denies a freshly generated message
	before it is committed. Applied in order; default empty = pass-through. See ``hooks/``."""

	communication: object = None
	"""Optional ``CommunicationPolicy`` governing turn order and message visibility (see ``communication/``).
	``None`` keeps the classic behavior: round-robin speaking order over the shared transcript. With a policy
	installed, ``run`` asks it for each next speaker (``first=`` is then ignored — the policy owns scheduling),
	the view pipeline filters transcript turns through ``policy.visible`` and appends ``policy.extra_segments``
	(delivered mail, pending-message pings, protocol instructions), and every committed turn flows through
	``policy.on_commit``. Policies are conversation-state: clones/branches get an independent deep copy.
	Runtime-only (not persisted by ``save``), like ``message_hooks``."""

	# --- rollout / data fields (dot-modifier sugar via @sugar_fields; storage is the ``_`` name) ---
	_turns: int | None = None
	"""Default number of turns for ``run``/``rollout`` when not overridden. Read/set via ``conv.turns()`` /
	``conv.turns(n)``."""
	_data: object = None
	"""Optional dataset / iterable of dict rows driving ``rollout`` (one conversation per row). Required only when a
	templated field uses ``dataset_field``. ``conv.data()`` / ``conv.data(ds)``."""
	_analyzer: object = None
	"""Optional ``analyze(conv) -> serializable`` callable, or a registered analyzer name (a name is required for
	multi-GPU spawn). Runs in-worker after each conversation. ``conv.analyzer()`` / ``conv.analyzer(fn)``."""
	_name: str | None = None
	"""Optional label; used to namespace job ids in a multi-lineup ``interlens.run``. ``conv.name()`` /
	``conv.name(s)``."""
	_seed: int = 0
	"""Base RNG seed for ``rollout`` (sample *i* gets ``seed + i``). ``conv.seed()`` / ``conv.seed(k)``."""
	_run_until: object = None
	"""Optional ``StopCondition`` (or list) applied on every ``run``/``rollout`` conversation — e.g. a
	``TokenBudget`` for matched-compute. ``conv.run_until()`` / ``conv.run_until(cond)``."""

	def __post_init__(self):
		self.participants = tuple(self.participants)
		names = [p.name for p in self.participants]
		if len(names) != len(set(names)):
			raise ValueError(f"participant names must be unique, got {names}")
		if self.moderator_name in names:
			raise ValueError(f"moderator_name {self.moderator_name!r} collides with a participant name")
		self._pending_capture: CaptureRequest | None = None
		# Seed the shared scenario as a moderator turn — but only when starting fresh (so a branched/loaded
		# conversation is not re-seeded) AND the framing is already a concrete string. A data-parameterized framing
		# (contains ``dataset_field``) is NOT seeded here: it is resolved per row and seeded during rollout
		# expansion. ``None`` = no framing; ``""`` still seeds a blank turn so the first speaker has a non-empty view.
		if self.shared_context is not None and not has_fields(self.shared_context) and len(self.transcript) == 0:
			self.transcript.append(self.moderator_name, self.shared_context)

	def _after_set(self, original) -> None:
		# A copy-on-write clone gets an INDEPENDENT transcript (so branches / per-row rollout copies diverge without
		# corrupting each other) and no in-flight capture. Participants are shared by reference (zero GPU cost).
		# A communication policy is conversation-state (mailboxes, scheduling counters) — deep-copied so clones
		# never share delivery state.
		self.transcript = self.transcript.copy()
		self._pending_capture = None
		if self.communication is not None:
			import copy
			self.communication = copy.deepcopy(self.communication)

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

		multiparty = len(self.participants) > 2
		for message in (*self.transcript, *extra):
			if self.communication is not None and not self.communication.visible(message, participant, self):
				continue
			is_other = message.author != participant.name
			role = participant.others_role if is_other else participant.self_role
			origin = "moderator" if message.author == self.moderator_name else "turn"
			content = message.content
			reasoning = self._reasoning_for(participant, message)
			if reasoning:
				content = f"<reasoning>\n{reasoning}\n</reasoning>\n{content}"
			seg_author = message.author
			if is_other and multiparty:
				# N-party (n>2): label each other-speaker turn inline with its author so the speaker can tell
				# its several counterparts apart. Two turns from two *different* others (B then C, before A
				# speaks again) is a run of consecutive ``others_role`` segments; on strict-alternation families
				# ``finalize_view``'s merge already author-prefixes such a run, but permissive templates skip the
				# merge and would otherwise render both as anonymous same-role turns. Labelling here is
				# template-agnostic; clearing ``author`` keeps the strict-template merge from re-prefixing an
				# already-labelled turn. A 2-party conversation never has multi-other runs, so it is left as-is.
				content = f"{message.author}: {content}"
				seg_author = None
			segments.append(ViewSegment(role=role, content=content, origin=origin, author=seg_author))

		if self.communication is not None:
			segments.extend(self.communication.extra_segments(self, participant))

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
		if self.communication is not None:
			self.communication.on_commit(message, self)
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
		its ``name`` (str), or its index (int) — resolved via ``_resolve_participant`` (raises if it isn't in this
		conversation).

		Stop conditions are combined from three sources (any of which stops the run): ``until`` (this call), the
		conversation's own ``run_until`` field, and any ambient ``with StopCondition(...):`` blocks. A condition may
		also cap each turn's tokens (``turn_cap``) — e.g. a ``TokenBudget`` shrinks the final turn to land on budget.
		Conditions are ``reset()`` at the start so a reused instance doesn't leak state. ``turns`` defaults to the
		conversation's ``turns`` field; at least one of turns / a stop condition must be present.

		``prompt`` (optional) is appended to the transcript **before** the run: a ``str`` is attributed to the LAST
		participant (so ``first`` replies to it), a ``Message`` is appended as-is, ``None`` appends nothing. It
		appends to the current end and never resets/reseeds.
		"""
		self._check_resolved("run")
		if turns is None:
			turns = self._turns
		stop = self._resolve_stop(until)
		if turns is None and stop is None:
			raise ValueError("run requires at least one of `turns`, a `run_until`/`until` stop condition, or an "
			                 "ambient `with StopCondition(...)` block")
		self._append_prompt(prompt)
		if stop is not None:
			stop.reset()

		start = self._resolve_participant(first) if first is not None else 0
		n = len(self.participants)
		i = 0
		while turns is None or i < turns:
			cap = stop.turn_cap(self) if stop is not None else None
			if self.communication is not None:
				# the communication policy owns scheduling; None = no one is due, which ends the run
				speaker = self.communication.next_speaker(self)
				if speaker is None:
					break
				message = self.step(speaker, max_new_tokens=self._cap_for(speaker, cap))
			else:
				message = self.step(self.participants[(start + i) % n],
				                    max_new_tokens=self._turn_budget(start, i, cap))
			i += 1
			# A hook may have denied the turn (message is None); only a committed message is checked for stopping.
			if message is not None and stop is not None and stop.should_stop(self, message):
				break
		return self.transcript

	@staticmethod
	def _cap_for(speaker: Participant, cap: int | None) -> int | None:
		"""Bound a stop-condition ``turn_cap`` by ``speaker``'s own configured cap (policy-scheduled path)."""
		if cap is None:
			return None
		own = getattr(speaker, "max_new_tokens", None)
		return cap if own is None else min(own, cap)

	def _turn_budget(self, start: int, i: int, cap: int | None) -> int | None:
		"""Bound the next turn's ``max_new_tokens`` by a stop-condition ``cap`` AND the speaker's own configured cap
		(so a budget never *raises* a participant's token limit). ``None`` when there is no cap."""
		if cap is None:
			return None
		speaker = self.participants[(start + i) % len(self.participants)]
		own = getattr(speaker, "max_new_tokens", None)
		return cap if own is None else min(own, cap)

	def _resolve_stop(self, until):
		"""Combine this call's ``until`` with the conversation's ``run_until`` field and any ambient
		``with StopCondition`` blocks into one condition (any-of), or ``None`` if there are none."""
		conditions: list = []
		for source in (until, self._run_until):
			if source is None:
				continue
			conditions.extend(source if isinstance(source, (list, tuple)) else [source])
		conditions.extend(active_stop_conditions())
		if not conditions:
			return None
		return conditions[0] if len(conditions) == 1 else AnyStopCondition(conditions)
	
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

	def _resolve_participant(self, participant: ParticipantLike) -> int:
		"""Resolves a participant from a participant object, name, or index. Returns the index of the participant within self.participants. Raises an error if that participant does not exist in this Conversation."""
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

	def participant(self, which: ParticipantLike) -> Participant:
		"""Return one of this conversation's participants, resolved from a ``Participant`` object, its ``name``
		(str), or its index (int). Raises (via ``_resolve_participant``) if it isn't in this conversation."""
		return self.participants[self._resolve_participant(which)]

	def view(self, pov: ParticipantLike, extra=()) -> list[dict]:
		"""The full ``[{role, content}]`` view ``pov``'s model is conditioned on — the **real generation input**:
		system block (its private ``system_prompt`` + ``shared_system_prompt``) → ``private_context`` → the
		transcript role-swapped to ``pov``, then **context-fit** and **family-flattened**. This is exactly what
		``step`` / ``sample`` feed to ``generate``. Unlike ``transcript.render_roles`` (transcript turns only, no
		framing or fitting), it reflects everything the model actually sees. ``pov`` is a ``ParticipantLike`` (name
		/ index / participant); ``extra`` renders temporary, uncommitted messages (as ``sample`` does)."""
		return self._view(self.participant(pov), extra=extra)

	def render_templated(self, pov: ParticipantLike, *, extra=(), add_generation_prompt: bool = False,
	                     tokenize: bool = False):
		"""The full ``view`` run through ``pov``'s tokenizer chat template — the **exact prompt its model sees**,
		special/control tokens and all (a str, or token ids with ``tokenize=True``). This is the truthful
		counterpart to ``transcript.render_templated``, which templates the transcript turns ONLY (no system /
		private framing, no context-fit). Requires a local ``ModelParticipant`` (needs a tokenizer)."""
		participant = self.participant(pov)
		tokenizer = getattr(participant, "tokenizer", None)
		if tokenizer is None:
			raise TypeError(f"{type(participant).__name__} {participant.name!r} has no tokenizer; "
			                f"render_templated needs a local ModelParticipant")
		return tokenizer.apply_chat_template(self.view(pov, extra=extra), tokenize=tokenize,
		                                     add_generation_prompt=add_generation_prompt)

	# --- branching & ephemeral sampling --------------------------------------------------------------------

	def branch(self) -> "Conversation":
		"""Fork into a new ``Conversation`` that **reuses the same participant objects** (shared weights, zero GPU
		cost) with a copied, independent transcript. The branch can diverge freely; the original is untouched. This
		is exactly a no-op copy-on-write clone (``self.set()``). To fork from a specific point in the history rather
		than the end, use ``branch_from``."""
		return self.set()

	def branch_from(self, ref: MessageRef) -> "Conversation":
		"""Fork a new conversation whose history is this one's turns **up to and including** the turn ``ref`` — i.e.
		branch as if the conversation had stopped right after ``ref``, ready for a different continuation. ``ref`` is
		a ``MessageRef``: an ``int`` index (negatives count from the end) or the ``Message`` object itself (matched
		by identity). The original is untouched; the fork shares participants (zero GPU cost)."""
		cut = self.transcript.resolve_index(ref)  # resolve against the original (the fork holds copies, new identities)
		fork = self.branch()
		fork.transcript.rewind(to=cut)
		return fork

	# --- in-place history editing (delegated to the transcript) --------------------------------------------

	def rewind(self, *, to: MessageRef) -> "Conversation":
		"""Rewind in place so the turn ``to`` becomes the new last turn, dropping everything after it (returns
		``self`` for chaining). ``to`` is a ``MessageRef`` (int index, negatives allowed, or a ``Message`` object).
		Mutates this conversation — use ``branch_from`` instead to keep the original. See ``Transcript.rewind``."""
		self.transcript.rewind(to=to)
		return self

	def edit(self, ref: MessageRef, content: str | None = None, *, author: str | None = None, **metadata) -> Message:
		"""Edit a committed past turn in place and return it (see ``Transcript.edit``): ``ref`` is a ``MessageRef``
		(int index, negatives allowed, or a ``Message`` object matched by identity), and ``content`` / ``author`` /
		``**metadata`` are the fields to change. Editing the returned ``Message``'s fields directly works too, since
		the transcript holds it by reference."""
		return self.transcript.edit(ref, content, author=author, **metadata)

	def reset(self) -> "Conversation":
		"""Return the conversation to its fresh, pre-``run`` state: empty the transcript, then **re-seed** the
		``shared_context`` moderator turn (exactly as ``__post_init__`` does on a fresh conversation). Use this
		rather than ``transcript.clear()`` when you want to rerun the same scenario — the raw ``transcript.clear()``
		drops the ``shared_context`` framing too, whereas ``reset`` restores it."""
		self.transcript.clear()
		if self.shared_context is not None:
			self.transcript.append(self.moderator_name, self.shared_context)
		return self

	@overload
	def sample(self, speaker: ParticipantLike, message: str | None = None, *, as_author: str | None = None,
	           steering=None, capture=None, patch=None, return_logprobs: bool = False,
	           max_new_tokens: int | None = None) -> Message: ...
	@overload
	def sample(self, speaker: "list[ParticipantLike] | tuple[ParticipantLike, ...]", message: str | None = None, *,
	           as_author: str | None = None, steering=None, capture=None, patch=None, return_logprobs: bool = False,
	           max_new_tokens: int | None = None) -> "dict[str, Message]": ...

	def sample(self, speaker, message=None, *, as_author=None, steering=None, capture=None, patch=None,
	           return_logprobs: bool = False, max_new_tokens: int | None = None):
		"""Ephemerally sample a response **without mutating the transcript** — a pure read of current state, safe to
		call repeatedly / in a loop. ``speaker`` is a ``ParticipantLike`` (name / index / ``Participant``); pass a
		**list or tuple** of them to sample each and get back ``{name: Message}`` instead of a single ``Message``
		(see also ``sample_all``). ``message`` is an optional temporary incoming turn; it defaults to being
		attributed to the **moderator** (a neutral, external voice — so "What do you think of Bob?" reads as an
		interviewer asking, NOT as Bob speaking). Pass ``as_author="bob"`` to make it read as that participant's
		turn instead (e.g. "what would you say if Bob had just said X?"). The same interp options as ``step`` are
		honored on each ephemeral generation."""
		self._check_resolved("sample")
		if isinstance(speaker, (list, tuple)):
			return {self.participant(s).name: self.sample(s, message, as_author=as_author, steering=steering,
			                                              capture=capture, patch=patch, return_logprobs=return_logprobs,
			                                              max_new_tokens=max_new_tokens) for s in speaker}
		speaker = self.participant(speaker)
		extra = []
		if message is not None:
			extra = [Message(author=as_author or self.moderator_name, content=message)]
		return speaker.generate(self._view(speaker, extra=extra), steering=steering, capture=capture,
		                        patch=patch, return_logprobs=return_logprobs, turn=len(self.transcript),
		                        max_new_tokens=max_new_tokens)

	def sample_all(self, message: str | None = None, *, as_author: str | None = None, steering=None,
	               capture=None, patch=None, return_logprobs: bool = False,
	               max_new_tokens: int | None = None) -> "dict[str, Message]":
		"""Ephemerally sample **every** participant's response — a convenience for
		``sample(list(self.participants), ...)``. Returns ``{name: Message}``; the transcript is untouched. Handy
		for "what does each model say to this right now?"."""
		return self.sample(list(self.participants), message, as_author=as_author, steering=steering,
		                   capture=capture, patch=patch, return_logprobs=return_logprobs, max_new_tokens=max_new_tokens)


	# --- data-driven rollout -------------------------------------------------------------------------------

	@property
	def row(self) -> dict:
		"""The dataset row that produced this conversation in a data-driven ``rollout`` (the same dict the
		``dataset_field``s resolved against), or ``{}`` outside a rollout. Read it in an ``analyzer`` to reach per-row
		side data — labels, gold answers, ids — WITHOUT templating it into the model's view (so it never leaks into
		the conversation). Travels with the conversation across the spawn boundary."""
		return getattr(self, "_row", {})

	def _check_resolved(self, action: str) -> None:
		"""Guard against running/sampling a conversation whose framing still contains unresolved ``dataset_field``s
		(a data-parameterized recipe). Such a conversation is a template for ``rollout``, not a live dialogue."""
		templated = has_fields(self.shared_context) or has_fields(self.shared_system_prompt) or any(
			has_fields(getattr(p, "system_prompt", None)) for p in self.participants)
		if templated:
			raise ValueError(
				f"cannot {action}() this conversation: its framing contains unresolved dataset_field(...) "
				f"placeholders — it is a data-parameterized recipe. Call rollout() to expand it over data(), then "
				f"read a finished conversation from report.results[job_id].conversation.")

	def _expand(self, n: int | None, seed: int, stop):
		"""Expand this recipe into ``(job_id, conversation)`` jobs — one per data row, or ``n`` seeded copies.

		The dataset is **streamed, never materialized**: rows are pulled one at a time via ``_iter_rows`` (works for
		an in-memory list, a map-style HF ``Dataset``, or a streaming ``IterableDataset`` — a 100-TB corpus is fine,
		nothing is loaded up front). Each job is an INDEPENDENT copy-on-write clone with its per-row framing resolved,
		its participants seeded (``seed + i``) and per-row-templated, ``data`` cleared, the combined stop condition
		attached, and the source row stashed on ``conv.row`` for the analyzer. Resolution happens here (once,
		deterministically → job *i* ⟷ row *i*), so resume stays correct and no dataset iterator leaks into a running
		conversation."""
		if self._data is None and n is None:
			raise ValueError("rollout needs either data() (one conversation per row) or n= (that many copies)")
		jobs = []
		for i, row in self._iter_rows(n):
			job_id = f"row_{i:05d}" if self._data is not None else f"rollout_{i:04d}"
			participants = tuple(self._expand_participant(p, row, seed + i) for p in self.participants)
			job = self.set(participants=participants, data=None, run_until=stop,
			               shared_context=resolve(self.shared_context, row),
			               shared_system_prompt=resolve(self.shared_system_prompt, row))
			job._row = dict(row) if row else {}      # the source row, available to the analyzer as conv.row
			job.reset()  # clear the (empty) transcript and seed the now-resolved shared_context
			jobs.append((job_id, job))
		return jobs

	def _iter_rows(self, n: int | None):
		"""Yield ``(index, row)`` lazily, capped at ``n``. For ``data()`` this iterates the dataset ONE row at a time
		(no ``list(...)`` — so map-style ``Dataset``s stay Arrow-backed on disk and streaming ``IterableDataset``s are
		consumed once); ``n`` defaults to ``len(data)`` when the length is known, else all rows. With no data, yields
		``(i, {})`` for ``i`` in ``range(n)``."""
		if self._data is None:
			yield from ((i, {}) for i in range(n))
			return
		try:
			total = len(self._data)               # map-style Dataset: O(1) metadata, no materialization
		except TypeError:
			total = None                           # streaming IterableDataset: unknown length
		limit = total if n is None else (n if total is None else min(n, total))
		for i, row in enumerate(self._data):       # one row at a time
			if limit is not None and i >= limit:
				break
			yield i, row

	@staticmethod
	def _expand_participant(p, row: dict, seed: int):
		"""One per-job participant copy: its ``system_prompt`` resolved against ``row`` and (for local models that
		sample) its ``seed`` set so rollouts diverge but stay reproducible. Weights are shared by reference."""
		changes = {}
		sp = getattr(p, "system_prompt", None)
		if has_fields(sp):
			changes["system_prompt"] = resolve(sp, row)
		if hasattr(p, "seed"):  # local ModelParticipant — per-rollout seed offset
			changes["seed"] = seed
		return p.set(**changes) if changes else p.set()

	def rollout(self, n: int | None = None, *, devices=None, out_dir=None, resume: bool = False,
	            batched: bool = True, max_batch_size: int | None = None, seed: int | None = None) -> "RunReport":
		"""Run many conversations from this one recipe and return a ``RunReport`` — the benchmark/scale entry point.

		**Rollout does NOT mutate this conversation.** It makes an independent copy-on-write clone per job and runs
		*those*; ``self`` stays the unrun recipe. Finished conversations live in ``report.results[job_id].conversation``
		(and their transcripts / analyses on the same ``RunResult``) — that is where to ``sample()`` or inspect
		afterwards, NOT on the original.

		Two modes: with ``data()`` set, expands to ONE conversation per row (job ids ``row_00000``…), resolving each
		templated field (``dataset_field``) against the row; otherwise expands to ``n`` seeded copies of one scenario
		(job ids ``rollout_0000``…). ``n`` defaults to ``len(data)``. Sample *i* gets ``seed + i`` (``seed`` defaults
		to the conversation's ``seed`` field). Any ambient ``with StopCondition(...)`` blocks and the ``run_until``
		field are captured now and attached to every job (so they survive the spawn boundary).

		Parallel by default on two axes (see :func:`interlens.run`): one worker process per device, and batched
		co-stepping within each device. ``batched=False`` gives the token-identical DETERMINISTIC path.
		"""
		from .runner.pool import run_jobs
		seed = self._seed if seed is None else seed
		stop = self._combined_stop_for_jobs()
		jobs = self._expand(n, seed, stop)
		return run_jobs(jobs, devices=devices, out_dir=out_dir, resume=resume, batched=batched,
		                max_batch_size=max_batch_size)

	def _jobs_for_run(self, index: int):
		"""Expand this conversation into namespaced ``(job_id, conversation)`` jobs for ``interlens.run``: one per
		``data()`` row if it has data, else a single job. Job ids are prefixed with the conversation's ``name``
		(default ``conv{index}``) so a mixed multi-lineup run keeps unique, resumable ids."""
		prefix = self._name or f"conv{index}"
		stop = self._combined_stop_for_jobs()
		if self._data is not None:
			jobs = self._expand(None, self._seed, stop)
			return [(f"{prefix}/{jid}", conv) for jid, conv in jobs]
		single = self.set(run_until=stop)
		single._check_resolved("run")
		return [(prefix, single)]

	def _combined_stop_for_jobs(self):
		"""Capture ambient ``with StopCondition`` blocks + this conversation's ``run_until`` into a single value to
		attach to each job (resolved now, since the ambient ContextVar does not cross the spawn boundary). Returns a
		condition, a list, or ``None``."""
		conditions = list(active_stop_conditions())
		if self._run_until is not None:
			conditions.extend(self._run_until if isinstance(self._run_until, (list, tuple)) else [self._run_until])
		if not conditions:
			return None
		return conditions[0] if len(conditions) == 1 else list(conditions)

	# --- persistence ---------------------------------------------------------------------------------------

	def save(self, directory) -> None:
		"""Persist the conversation: the transcript (``transcript.json``) + the recipe (``conversation.json`` — the
		participants' own constructor kwargs + scenario framing/policies, no weights)."""
		import json
		from pathlib import Path
		from .participant.serialize import participant_to_dict
		from .transcript import SCHEMA_VERSION

		directory = Path(directory)
		directory.mkdir(parents=True, exist_ok=True)
		recipe = {
			"schema_version": SCHEMA_VERSION,
			"participants": [participant_to_dict(p) for p in self.participants],
			"shared_context": self.shared_context if not has_fields(self.shared_context) else None,
			"shared_system_prompt": self.shared_system_prompt if not has_fields(self.shared_system_prompt) else None,
			"moderator_name": self.moderator_name,
			"context_limit": self.context_limit,
			"reasoning_visibility": self.reasoning_visibility.value,
			"execution_mode": self.execution_mode.value,
		}
		(directory / "conversation.json").write_text(json.dumps(recipe, indent=2))
		self.transcript.save(directory / "transcript.json")

	@classmethod
	def load(cls, directory, devices="cuda") -> "Conversation":
		"""Rebuild a saved conversation: reconstruct (lazy) participants from the recipe and attach the saved
		transcript, resuming from that state (does NOT regenerate messages). Raises on an unsupported schema."""
		import json
		from pathlib import Path
		from .participant.serialize import participant_from_dict
		from .transcript import Transcript, SCHEMA_VERSION

		directory = Path(directory)
		recipe = json.loads((directory / "conversation.json").read_text())
		version = recipe.get("schema_version")
		if version != SCHEMA_VERSION:
			raise ValueError(f"checkpoint schema {version!r} is no longer supported (current {SCHEMA_VERSION}); "
			                 f"re-generate the run with the current interlens.")
		device = devices[0] if isinstance(devices, (list, tuple)) else devices
		participants = tuple(participant_from_dict(p, device=device) for p in recipe["participants"])
		return cls(
			participants=participants,
			transcript=Transcript.load(directory / "transcript.json"),
			shared_context=recipe.get("shared_context"),
			shared_system_prompt=recipe.get("shared_system_prompt"),
			moderator_name=recipe.get("moderator_name", "moderator"),
			context_limit=recipe.get("context_limit"),
			reasoning_visibility=ReasoningVisibility(recipe.get("reasoning_visibility", "strip")),
			execution_mode=ExecutionMode(recipe.get("execution_mode", "throughput")),
		)
