# `interlens.arena.negotiation.talking`

The **talking rational agent**: the composed Bayesian negotiator with a truthful templated voice.

`BayesianRationalPolicy` is mute — its beliefs are signal-starved under private information because the only
evidence it ever emits or consumes is offer movement. This module gives the SAME decision rule a message
channel, in a ladder of strictly increasing revelation, plus the inbound half (parsing counterparties'
statements into belief-grid conditioning). The decision rule is UNCHANGED by construction: the speaking
variants only add messages, and the listening variant changes only the belief posterior the existing rule is
applied to.

The ladder (`TalkingBayesianPolicy.VARIANTS`):

- `commit` (T1) — once, on its first turn: its concession schedule ("I accept any package worth at least
  `bar(r)` to me; the bar falls to my floor by the deadline"), computed from the live optimal-stopping
  reservation curve under current beliefs.
- `narrate` (T2) — each turn with a standing offer: whether that offer clears its CURRENT reservation bar and
  by how much, in its own points and on its own min-max-normalized 0-1 scale.
- `hint` (T3) — narrate + once, on its first turn: its ordinal top option on each issue (tops only — no
  scores, no threshold).
- `listen` (T4) — commit + narrate + hint + parse other seats' `talking_rational` statements (verbatim from
  other talking seats; from LLM text via a strict JSON convention it requests in its first-turn message) into
  soft, trust-discounted belief-grid conditioning.

`BabbleBayesianPolicy` is the control: fluent, on-topic, length-matched, state-INDEPENDENT boilerplate every
turn over the same mute decision rule — it separates "any speech helps" from "informative speech helps".

Honesty is a hard constraint, enforced by construction and gated offline: every emitted statement is a pure
function of the policy's live state (reservation curve, standing offer, own sheet), rendered by the same
functions an offline gate re-runs on the recorded view (see the rational_agents experiment's
`gate_talking_messages.py`). There is no bluffing arm here.

Message grammar: prose for the LLM audience plus one fenced `json` block per statement carrying
`{"talking_rational": {payload}}`. The scenario republishes a seat's `message` as plain text, so the block
is legible (and machine-parseable) in every other seat's view. :func:`statements_in` is the total parser —
anything malformed is dropped and counted, never raised.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `MESSAGE_KEY` |  |  |
| `STATEMENT_KINDS` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`BabbleBayesianPolicy`](BabbleBayesianPolicy.md) | The babble control: the mute decision rule plus fluent, on-topic, state-INDEPENDENT boilerplate every turn. |
| [`TalkingBayesianPolicy`](TalkingBayesianPolicy.md) | `BayesianRationalPolicy` with a truthful templated message channel and (optionally) inbound listening. |
| [`TalkingParticipant`](TalkingParticipant.md) | A :class:`PolicyParticipant` for talking policies: it merges the one-time `declaration` with the bound policy's per-turn `commentary` into the turn's public message, and (for listening policies) parses every `talking_rational` statement in the view into `state.statements` before the policy runs. |

## Functions

| Name | Summary |
|---|---|
| [`condition_on_commit`](condition_on_commit.md) | Fold a declared normalized walk-away floor into the posterior over the grid's reservation levels: a Gaussian log-likelihood `-(tau - floor)^2 / (2 scale^2)` per type, tempered by `strength` and `lam`. |
| [`condition_on_hint`](condition_on_hint.md) | Fold declared per-issue top options into the posterior: types whose evaluator peaks at the declared option on that issue match the claim (likelihood `reliability`), the rest `1 - reliability`, tempered by `strength` and the state's own damping `lam`. |
| [`condition_on_narration`](condition_on_narration.md) | Fold "this package is above/below my bar" into the posterior — exactly the accept/reject evidence `observe_response` implements, with the claim's truth value playing the vote. |
| [`statements_in`](statements_in.md) | Every well-formed talking-rational statement in `text`, plus the census the honesty audit needs. |
