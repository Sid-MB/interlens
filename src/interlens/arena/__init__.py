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

"""Scoreable multi-agent evaluations on interlens: scenarios, episode drivers, and exact scoring.

The arena turns interlens from a conversation harness into an evaluation harness: a ``Scenario`` defines a
game (solver-verified instance generation, per-seat private framing, a turn protocol with structured JSON
actions, early termination, exact scoring), and the engine plays it through any ``Participant`` — hosted-API
or local — as concurrently as the backend allows, persisting every episode to one JSON schema.

Quickstart::

    from interlens import APIParticipant, UsageMeter
    from interlens.arena import EpisodePool, EpisodeStore
    from interlens.arena.scenarios import Negotiation
    import asyncio

    scenario = Negotiation()
    instance = scenario.generate_instance(level=0, seed=1)      # solver-verified: exact ceiling + optimum
    meter = UsageMeter(budget=20.0)
    player = APIParticipant(name="player", model_id="claude-sonnet-5", meter=meter, turn_token_floor=2048)
    pool = EpisodePool(EpisodeStore("episodes/"), meter=meter)
    episode = asyncio.run(pool.run_episode(scenario, instance, "team", player))
    print(episode.outcome, episode.usage(), meter.summary())

Optional Inspect integration (``pip install interlens[inspect]``): ``interlens.arena.inspect`` exposes the
bundled scenarios as ``inspect eval``-runnable tasks.
"""

from .schema import (Episode, EpisodeStore, Instance, PERSONAS, SeatRequest, TurnRecord,
                     load_instances, save_instances)
from .scenario import Scenario
from .actions import (Accept, Action, Deal, LEGALITY, Offer, OfferId, OfferRegistry, ParseResult,
                      Pass, Propose, Reject, SYNTAX, Walk, action_from_json, parse_action)
from .oracles import Oracle, OracleRecord, OracleVerdict, annotate
from .engine import (BatchedEpisodePool, EMPTY_TURN_PLACEHOLDER, EpisodePool, EpisodeRun,
                     GenerationFailureBudgetExceeded, TURN_SIGNATURES, gen_failures, truncation_budget,
                     turn_signatures)
from .refusal import RefusalLadder, is_refusal
from .ratchet import DifficultyRatchet, found_level
from .rollouts import RolloutConfigMismatch, RolloutSet, config_fingerprint, rollout
from .replay import ReplayError, replay_episode, rescore
from .gates import check_reasoning_leak, check_template_fidelity, scenario_smoke_views
from .views import build_view, extract_json, strip_think

__all__ = [
	"Scenario",
	"Instance",
	"SeatRequest",
	"TurnRecord",
	"Episode",
	"EpisodeStore",
	"PERSONAS",
	"save_instances",
	"load_instances",
	# formal-action layer
	"Action",
	"Propose",
	"Accept",
	"Reject",
	"Walk",
	"Pass",
	"Deal",
	"OfferId",
	"Offer",
	"OfferRegistry",
	"ParseResult",
	"parse_action",
	"action_from_json",
	"SYNTAX",
	"LEGALITY",
	# oracle layer
	"Oracle",
	"OracleVerdict",
	"OracleRecord",
	"annotate",
	"EpisodePool",
	"BatchedEpisodePool",
	"EpisodeRun",
	# generation-failure visibility: the placeholder the engine substitutes for a turn it could not
	# generate, the detector that finds those turns in a stored episode, and the fail-loud budget
	"EMPTY_TURN_PLACEHOLDER",
	"gen_failures",
	"GenerationFailureBudgetExceeded",
	# the wider per-turn screen: the placeholder's OTHER cause (a model burning its cap inside <think>) is
	# invisible to the fabrication gate, parse_ok, and an empty-content check alike
	"turn_signatures",
	"TURN_SIGNATURES",
	# which of a stored turn's two recorded caps its output length may be compared against — the protocol's
	# number is not always the request's, and confusing them manufactures truncation
	"truncation_budget",
	# API-side refusal recovery: the content-preserving re-render ladder and its detector
	"RefusalLadder",
	"is_refusal",
	"DifficultyRatchet",
	"found_level",
	# rollout-set management: a directory of episodes + the manifest that says what produced them
	"RolloutSet",
	"rollout",
	"config_fingerprint",
	"RolloutConfigMismatch",
	"replay_episode",
	"rescore",
	"ReplayError",
	"check_template_fidelity",
	"check_reasoning_leak",
	"scenario_smoke_views",
	"build_view",
	"extract_json",
	"strip_think",
]
