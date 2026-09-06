# `census`

Module `interlens.arena.viz.census`

How much of an episode is actually play: the per-turn census, and the strip that puts it in the page header.

The existing contamination banner counts turns the ENGINE fabricated, and it is right to be loud about them. But
it is a screen for one cause, and a turn can carry nothing for reasons the engine never sees:

- a thinking model spends its entire per-turn budget inside an unterminated `<think>` block, so the harness
  substitutes the same placeholder text — with `gen_failed` false, because generation succeeded, it just never
  produced a visible answer;
- a move is rejected as illegal, the seat repeats itself on its one retry, and the turn is recorded as a pass;
- a seat talks and takes no formal action at all, which is legal play but is not a move.

All three render as an ordinary, well-formed, quiet turn. A campaign cell reached **24% silent turns while
passing every gate**, including the fabrication gate, because 0.000 fabricated was the honest answer to the only
question anyone was asking. This module asks the other questions, on one episode, and puts the answers where a
reader cannot walk past them: non-action rate, placeholder count, at-cap count, and the same three by round.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `AT_CAP_SLACK` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`at_cap`](at_cap.md) | Whether one payload turn spent essentially its whole generation budget. |
| [`census_strip`](census_strip.md) | The per-episode census as a compact header strip, always rendered when there are turns to count. |
| [`turn_census`](turn_census.md) | Count the ways this episode's turns carried nothing, from the payload's own turn rows. |
