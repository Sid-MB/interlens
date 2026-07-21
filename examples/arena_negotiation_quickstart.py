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

"""Arena quickstart: define a scenario -> generate instances -> run team + matched-compute solo arms -> score.

Runs the negotiation scenario with a hosted model in every seat (needs ANTHROPIC_API_KEY), under a hard
dollar cap. Usage:

    python examples/arena_negotiation_quickstart.py --model claude-sonnet-5 --n 2 --budget 10
"""
from __future__ import annotations

import argparse
import asyncio
import statistics

from interlens import APIParticipant, TokenBudget, UsageMeter
from interlens.arena import EpisodePool, EpisodeStore
from interlens.arena.scenarios import Negotiation


async def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--model", default="claude-sonnet-5")
	parser.add_argument("--n", type=int, default=2, help="instances (one team + one solo episode each)")
	parser.add_argument("--level", type=int, default=0, help="difficulty (0-4: feasible set shrinks)")
	parser.add_argument("--budget", type=float, default=10.0, help="hard dollar cap for the whole run")
	parser.add_argument("--out", default="episodes", help="episode store directory")
	args = parser.parse_args()

	scenario = Negotiation()
	instances = [scenario.generate_instance(args.level, seed) for seed in range(1, args.n + 1)]

	meter = UsageMeter(budget=args.budget)
	player = APIParticipant(name="player", model_id=args.model, meter=meter,
	                        thinking="disabled",     # deterministic turn sizing; drop for thinking-on runs
	                        turn_token_floor=2048)   # thinking-aware: never starve a reasoning model's turn
	store = EpisodeStore(args.out)
	pool = EpisodePool(store, meter=meter)

	# team arm: the full 6-party protocol, one episode per instance, all concurrent
	team = await pool.run_pool([
		dict(scenario=scenario, instance=inst, arm="team", participant=player) for inst in instances])
	print(f"team: {sum(bool(e.outcome.get('success')) for e in team)}/{len(team)} deals passed")

	# solo arm, matched compute: one omniscient mediator, budgeted at the team arm's median token spend
	median_tokens = int(statistics.median(e.tokens_out for e in team)) if team else 4000
	solo = await pool.run_pool([
		dict(scenario=scenario, instance=inst, arm="solo", participant=player,
		     budget=TokenBudget(per_conversation=median_tokens)) for inst in instances])
	print(f"solo (@{median_tokens} tokens): "
	      f"{sum(bool(e.outcome.get('success')) for e in solo)}/{len(solo)} deals passed")

	print(meter.summary())
	print(store.summary())


if __name__ == "__main__":
	asyncio.run(main())
