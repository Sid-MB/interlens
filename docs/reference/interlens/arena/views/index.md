# `interlens.arena.views`

Per-seat view construction + structured-action parsing for arena scenarios.

Views are family-agnostic role/content message lists; the participant applies the family-correct chat template
(`ModelParticipant`) or provider format (`APIParticipant`). Views alternate user/assistant with the seat's
own past turns as assistant turns and everyone else's (author-labelled) as merged user turns — the same
semantics as the core per-speaker view pipeline, specialized to a scenario's event list with per-seat private
events.

Family-agnostic means exactly that: the alternation here is *this seat's* speaking order, so a view legitimately
opens on the seat's OWN turn (the round-1 opener of a multi-round game, whose proposal is the first event in the
shared log) or repeats it (a rotation/round-boundary repeat). A strict template — Gemma's — rejects both; the
participant repairs the flattened view for its own family in `Participant.repair_view`. Do not repair here.

## Functions

| Name | Summary |
|---|---|
| [`build_view`](build_view.md) | Render `events` (`[{seat\|'MODERATOR', content, only?}]`, public unless `only` names seats) into an alternating per-speaker view for `seat`, ending with `phase_prompt` as the final user turn. |
| [`extract_json`](extract_json.md) | The last fenced JSON object in `text`, else the last balanced top-level `{...}` that parses. |
