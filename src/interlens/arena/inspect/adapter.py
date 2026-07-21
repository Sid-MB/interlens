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

"""The Inspect adapter core: a Participant backed by Inspect's model, the arena solver, and the scorer.

Thin glue by design — Inspect owns model access, per-sample concurrency, retry, logging, and native
token-usage tracking; interlens owns the game (the SAME ``EpisodePool``/``Scenario``/``MessagingPolicy``
machinery as outside Inspect — no duplicated engine). The bridge is one class: ``InspectModelParticipant``, an
interlens ``Participant`` whose ``generate`` posts an ``inspect_ai`` model call back onto the event loop.
Because the arena engine already runs blocking participants in worker threads, the whole engine — episode
pooling, budgets, retries, provisional forking — works under Inspect unchanged, and Inspect's own
``--max-samples`` concurrency runs many episodes at once (the solver holds no shared mutable state).

What the adapter adds on top of Inspect's native accounting: dollar cost per sample (``metadata['cost_usd']``,
priced by ``interlens.usage`` — Inspect tracks tokens natively but not dollars) and the arena outcome/usage
recorded in the sample store for the scorer and the viewer.
"""
from __future__ import annotations

import asyncio
import json

from inspect_ai.log import transcript
from inspect_ai.model import (ChatMessageAssistant, ChatMessageSystem, ChatMessageUser, GenerateConfig,
                              get_model)
from inspect_ai.scorer import Score, Target, accuracy, mean, scorer, stderr
from inspect_ai.solver import Generate, TaskState, solver

from ...communication import MessagingPolicy
from ...conversation import Conversation
from ...message import Message
from ...participant import Participant
from ...usage import UsageMeter
from ..engine import EpisodePool
from ..schema import Instance
from ..scenarios import SCENARIOS
from ..views import extract_json

_ROLE_TYPES = {"system": ChatMessageSystem, "user": ChatMessageUser, "assistant": ChatMessageAssistant}


def _to_chat_messages(view: list[dict]):
	return [_ROLE_TYPES[m["role"]](content=m["content"]) for m in view]


class InspectModelParticipant(Participant):
	"""An interlens ``Participant`` played by an Inspect model.

	``generate`` runs in a worker thread (that is how the engine and ``Conversation`` drive blocking
	participants), so it posts the async ``model.generate`` back onto the solver's event loop and blocks on
	the future — Inspect's connection limits and retries apply as usual. Usage telemetry lands in
	``Message.metadata`` under the same keys every other participant uses, so budgets, metering, and episode
	accounting work unchanged."""

	# Inspect providers accept a separate system message list entry; no alternation repair needed here
	# (provider-side handling), and the arena's views are already alternating.
	requires_alternating_roles = False

	def __init__(self, name: str, model=None, *, loop=None, meter: UsageMeter | None = None,
	             max_tokens: int = 2048, system_prompt: str | None = None):
		self.name = name
		self.model = model or get_model()
		self.model_id = str(self.model)
		self.loop = loop
		self.meter = meter
		self.max_tokens = max_tokens
		self.system_prompt = system_prompt
		self.private_context = ()

	def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
	             return_logprobs: bool = False, turn: int | None = None,
	             max_new_tokens: int | None = None) -> Message:
		if steering is not None or capture is not None or patch is not None or return_logprobs:
			raise NotImplementedError(
				f"InspectModelParticipant {self.name!r} has no local model: interp requests are unavailable.")
		config = GenerateConfig(max_tokens=max_new_tokens if max_new_tokens is not None else self.max_tokens)
		coro = self.model.generate(_to_chat_messages(view), config=config)
		loop = self.loop
		if loop is None:
			raise RuntimeError("InspectModelParticipant needs the solver's event loop (pass loop=)")
		output = asyncio.run_coroutine_threadsafe(coro, loop).result()
		usage = output.usage
		tokens_in = getattr(usage, "input_tokens", 0) or 0
		tokens_out = getattr(usage, "output_tokens", 0) or 0
		stop_reason = getattr(output, "stop_reason", None)
		metadata = {"model": self.model_id, "n_tokens": tokens_out, "n_tokens_in": tokens_in,
		            "stop_reason": stop_reason}
		if stop_reason in ("refusal", "content_filter"):
			metadata["refusal"] = True
		if self.meter is not None:
			metadata["cost_usd"] = self.meter.add(self.model_id, tokens_in, tokens_out,
			                                      refusal=bool(metadata.get("refusal")))
		return Message(author=self.name, content=output.completion or "", metadata=metadata)


def _instance_from_state(state: TaskState) -> tuple:
	metadata = state.metadata or {}
	instance = Instance.from_json(metadata["instance"])
	scenario = SCENARIOS[instance.scenario]()
	return scenario, instance, metadata


def _record_turns(state: TaskState, episode_json: dict) -> None:
	"""Mirror the episode into the sample's message list so ``inspect view`` renders the multi-agent flow:
	each turn as a seat-attributed assistant message, structured actions as transcript info events."""
	for turn in episode_json["turns"]:
		state.messages.append(ChatMessageAssistant(
			content=f"[{turn['seat']} — round {turn['round']}, {turn['phase']}]\n{turn['content']}"))
		if turn.get("parsed_action"):
			transcript().info({"seat": turn["seat"], "round": turn["round"], "phase": turn["phase"],
			                   "action": turn["parsed_action"]}, source="arena.action")


@solver
def arena_solver(arm: str = "team", communication: str = "round_robin",
                 turn_max_tokens: int = 2048, messaging_turns: int = 24):
	"""Play one arena instance (from the sample's metadata) with the evaluated model in every seat.

	``communication="round_robin"`` runs the scenario's published turn protocol through the arena engine;
	``"messaging"`` runs the autonomous point-to-point variant — each seat gets its private framing and the
	agents self-organize via ``send_message``/``read_message`` mailboxes (recorded as transcript events), with
	the finalizer's fenced ``{"answer"}``/``{"proposal"}`` JSON scored exactly as in the protocol mode."""

	async def solve(state: TaskState, generate: Generate) -> TaskState:
		scenario, instance, metadata = _instance_from_state(state)
		cfg = metadata.get("cfg") or None
		loop = asyncio.get_running_loop()
		meter = UsageMeter()
		if communication == "round_robin":
			participant = InspectModelParticipant("player", loop=loop, meter=meter,
			                                      max_tokens=turn_max_tokens)
			pool = EpisodePool(store=None)
			episode = await pool.run_episode(scenario, instance, arm, participant, cfg=cfg,
			                                 gen_config={"inspect": True})
			episode_json = episode.to_json()
			outcome = episode.outcome if episode.status == "done" else {"error": episode.error}
			usage = episode.usage()
		elif communication == "messaging":
			episode_json, outcome, usage = await asyncio.to_thread(
				_run_messaging_episode, scenario, instance, cfg, loop, meter, turn_max_tokens,
				messaging_turns)
		else:
			raise ValueError(f"unknown communication mode {communication!r}")
		_record_turns(state, episode_json)
		state.store.set("arena:outcome", outcome)
		state.store.set("arena:usage", usage)
		state.store.set("arena:episode_id", episode_json["episode_id"])
		state.store.set("arena:instance_id", instance.instance_id)
		state.metadata["cost_usd"] = meter.total_usd
		state.metadata["seat_framings"] = metadata.get("seat_framings", {})
		return state

	return solve


def _run_messaging_episode(scenario, instance, cfg, loop, meter, turn_max_tokens, turns):
	"""The messaging-mode episode: seats become autonomous agents over a ``MessagingPolicy`` conversation.
	Each agent's private framing is the scenario's per-seat system prompt; the deciding seat's last fenced
	action JSON is scored by feeding it through the scenario's own finalization path."""
	state = scenario.make_state(instance, "team", instance.seed, cfg=cfg)
	framings = scenario.seat_framings(state)
	seats = [spec["name"] for spec in scenario.seat_specs(state)]
	participants = tuple(
		InspectModelParticipant(seat, loop=loop, meter=meter, max_tokens=turn_max_tokens,
		                        system_prompt=framings.get(seat, ""))
		for seat in seats)
	policy = MessagingPolicy(agents=list(seats))
	conv = Conversation(participants=participants, communication=policy,
	                    shared_context="Work autonomously; communicate only via messages.")
	conv.run(turns=turns)
	# extract the deciding seat's final structured action from its own turns (latest wins)
	decider = seats[0] if scenario.name == "e5_relay" else seats[state["inst"].payload.get("proposer", 0)]
	final_action = None
	for message in conv.transcript:
		if message.author == decider:
			parsed = extract_json(message.content)
			if isinstance(parsed, dict) and ("answer" in parsed or "proposal" in parsed or "final" in parsed):
				final_action = parsed
	# feed the final action through the scenario's forced-finalization path so scoring stays exact
	fresh = scenario.make_state(instance, "team", instance.seed, cfg=cfg)
	if final_action is not None:
		# drive the protocol state machine to its finalization request and apply the extracted action
		while not fresh["done"]:
			pending = scenario.next_requests(fresh)
			request = pending[0]
			if request.phase in ("final_answer", "final_proposal"):
				scenario.apply(fresh, request, f"```json\n{json.dumps(final_action)}\n```")
			else:
				scenario.apply(fresh, request, "(worked via private messages)")
	else:
		while not fresh["done"]:
			request = scenario.next_requests(fresh)[0]
			scenario.apply(fresh, request, "(no answer produced)")
	outcome = scenario.score(fresh)
	episode_json = {
		"episode_id": f"messaging-{instance.instance_id}",
		"turns": [
			{"seat": m.author, "round": i, "phase": "messaging", "content": m.content,
			 "parsed_action": (m.metadata.get("comm_sends") or m.metadata.get("comm_read"))}
			for i, m in enumerate(conv.transcript) if m.author != conv.moderator_name],
		"comm_events": list(policy.events),
	}
	from ...usage import transcript_usage
	usage = transcript_usage(conv.transcript)
	return episode_json, outcome, usage


@scorer(metrics={"success": [accuracy(), stderr()], "primary": [mean()]})
def scenario_scorer():
	"""Score from the scenario's exact outcome (stored by the solver): ``success`` (bool) and ``primary``
	(the scenario's normalized primary metric), with the full outcome dict in the score metadata."""

	async def score(state: TaskState, target: Target) -> Score:
		outcome = state.store.get("arena:outcome") or {}
		return Score(
			value={"success": 1.0 if outcome.get("success") else 0.0,
			       "primary": float(outcome.get("primary") or 0.0)},
			answer=json.dumps(outcome.get("deal") or outcome.get("answer") or None),
			metadata={"outcome": outcome, "usage": state.store.get("arena:usage"),
			          "episode_id": state.store.get("arena:episode_id"),
			          "instance_id": state.store.get("arena:instance_id")},
		)

	return score
