# `policy_participant`

Module `interlens.arena.negotiation.policy_participant`

`PolicyParticipant`: a state-dependent pure-Python seat that computes its move from a bound policy.

Where `ScriptedParticipant` cycles fixed strings ignoring the conversation, a `PolicyParticipant` *reads*
the view, reconstructs the structured negotiation state (the offer registry, standing offer, its own and
opponents' past proposals, the round), asks a bound `policy(state) -> action` for a typed action
(`Propose` / `Accept` / `Reject` / `Walk`), and emits it in the **same fenced-JSON envelope an LLM
seat produces** — so a computable rational agent and an LLM are interchangeable seats in one scenario.

It holds no model/activations, so (like `ScriptedParticipant`) it raises on any interp request
(steering / capture / patch / logprobs) rather than silently ignoring it.

Two ways to supply the state each turn:

- **default view reconstruction** — parse the fenced-JSON actions already in the view (role `assistant` =
  this seat's past turns, role `user` = others'), rebuild the offer ledger with monotonic ids, and infer
  the round from this seat's completed turns. This keeps the participant symmetric with LLM seats (it reads
  exactly what an LLM reads) without any English NLP.
- **`state_provider`** — an injected `callable(view) -> NegotiationState` for scenarios that already track
  structured state (e.g. the arena scenario handing over its authoritative registry).

## Classes

| Name | Summary |
|---|---|
| [`PolicyParticipant`](PolicyParticipant.md) | A pure-Python negotiation seat driven by a bound `policy`. |
