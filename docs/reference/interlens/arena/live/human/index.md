# `human`

Module `interlens.arena.live.human`

`HumanParticipant`: a seat played by a person in a browser.

The person is a participant like any other. `Participant.generate` is synchronous and the engine already runs
it in `asyncio.to_thread` (`arena/engine.py`), so a seat that blocks for two minutes while somebody decides
what to offer blocks a worker thread and nothing else — no async plumbing, no engine change.

The split of responsibility is deliberate and is the thing to preserve:

- the PARTICIPANT parses the state out of its own view, publishes an `awaiting_human` event describing what
  may legally be done, and blocks on a queue;
- the SERVER validates the submitted form and assembles the message, because validation needs the deal space and
  the offer registry and belongs on the side that can answer a POST with a 400;
- the message the server enqueues goes through `arena.actions.action_message` — the SAME renderer LLM seats'
  output is parsed back out of — so a human turn is byte-identical in form to a model turn. Nothing downstream
  (the scenario parser, the oracles, the visualizer, an exported dataset row) can tell them apart except by the
  `occupant` stamp, which is exactly the property that makes a mixed human/model game measurable.

Never enqueue an unvalidated submission: the engine reads empty content as a well-formed no-op turn (it
substitutes `EMPTY_TURN_PLACEHOLDER`), so a mistyped form would silently become the player passing.

Owned by lane A.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `FINAL_PROPOSAL` |  |  |
| `FINAL_VOTE` |  |  |
| `TURN` |  |  |
| `logger` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`HumanParticipant`](HumanParticipant.md) | A negotiation seat whose moves come from a browser. |
| [`PendingRequest`](PendingRequest.md) | One open ask of a human seat — what the browser renders a form from, and what the server validates a submission against. |
| [`SessionStopped`](SessionStopped.md) | Raised inside a blocked :meth:`HumanParticipant.generate` when the session is stopped. |

## Functions

| Name | Summary |
|---|---|
| [`build_human_message`](build_human_message.md) | Turn a validated browser form into the message a human seat plays — the assembly half of the split above. |
| [`legal_actions`](legal_actions.md) | What this seat may legally submit right now, as `{can_accept, can_reject, can_offer, can_walk, can_pass}` — the form's rules and the server's validation, computed once from one state. |
| [`phase_of`](phase_of.md) | The scenario phase this state describes: :data:`FINAL_VOTE` on the forced-final ballot, :data:`FINAL_PROPOSAL` on the turn that tables it, else an ordinary :data:`TURN`. |
| [`sheet_json`](sheet_json.md) | A seat's private score sheet as the dock renders it: `{agent, values, threshold}`. |
