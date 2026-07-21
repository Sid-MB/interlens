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

"""The info-relay task on the ASYNC MESSAGING communication style.

Instead of the published round-robin protocol, the four analysts run as autonomous agents with no shared
transcript: each holds its private shard (the scenario's per-seat framing) and communicates only via
``send_message`` / ``read_message`` mailboxes (a ``MessagingPolicy``), with ping-driven scheduling. The
finalizer's last fenced ``{"answer": ...}`` is scored by the scenario's exact scorer.

Runs with a hosted model (needs ANTHROPIC_API_KEY):

    python examples/arena_relay_messaging.py --model claude-sonnet-5 --turns 16
"""
from __future__ import annotations

import argparse

from interlens import APIParticipant, Conversation, MessagingPolicy, UsageMeter, transcript_usage
from interlens.arena.scenarios import InfoRelay
from interlens.arena.views import extract_json


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--model", default="claude-sonnet-5")
	parser.add_argument("--turns", type=int, default=16, help="total agent activations")
	parser.add_argument("--level", type=int, default=0, help="hardness (0-4)")
	parser.add_argument("--seed", type=int, default=1)
	args = parser.parse_args()

	scenario = InfoRelay()
	instance = scenario.generate_instance(args.level, args.seed)
	state = scenario.make_state(instance, "team", args.seed)
	framings = scenario.seat_framings(state)              # each seat's private shard + rules
	seats = [spec["name"] for spec in scenario.seat_specs(state)]

	meter = UsageMeter()
	participants = tuple(
		APIParticipant(name=seat, model_id=args.model, meter=meter, turn_token_floor=2048,
		               thinking="disabled",
		               system_prompt=(framings[seat]
		                              + f"\n\nThe finalizer is {seats[0]}. When you are the finalizer and "
		                              "confident, include your final fenced JSON {\"answer\": <number>}."))
		for seat in seats)
	policy = MessagingPolicy(agents=seats)
	conv = Conversation(participants=participants, communication=policy,
	                    shared_context="Work autonomously; communicate only via messages.")
	conv.run(turns=args.turns)

	# score the finalizer's last structured answer with the scenario's exact scorer
	answer = None
	for message in conv.transcript:
		if message.author == seats[0]:
			parsed = extract_json(message.content)
			if isinstance(parsed, dict) and "answer" in parsed:
				answer = parsed
	fresh = scenario.make_state(instance, "team", args.seed)
	while not fresh["done"]:
		request = scenario.next_requests(fresh)[0]
		if request.phase == "final_answer" and answer is not None:
			import json
			scenario.apply(fresh, request, f"```json\n{json.dumps(answer)}\n```")
		else:
			scenario.apply(fresh, request, "(worked via private messages)")
	outcome = scenario.score(fresh)

	print(f"gold={instance.payload['gold']}  answer={outcome['answer']}  success={outcome['success']}")
	print(f"message traffic: {sum(1 for e in policy.events if e['event'] == 'send')} sends, "
	      f"{sum(1 for e in policy.events if e['event'] == 'read')} reads")
	print("usage:", transcript_usage(conv.transcript))
	print(meter.summary())


if __name__ == "__main__":
	main()
