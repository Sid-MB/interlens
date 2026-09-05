# `interlens.arena.viz.assets.js_transcript`

Browser layer, part 3: the transcript — turn cards, the scrubber, and lazy prompt bodies.

A turn card wears its action type: a coloured left edge, a chip with a glyph and the word, and a dashed edge when
the seat was a computable policy rather than a model. The header is sticky, so scrolling a long reasoning trace
never loses track of whose turn it is, and clicking it selects the turn (which lights up the deal that turn put on
the chart).

**A hazard note comes before the turn's analysis, not after it.** "This turn is not what it looks like" — the
engine fabricated it, or generation produced no publishable answer — has to reach a reader before the columns
that discuss what the seat chose, because those columns are discussing a non-event.

**Prompt bodies are built on first open, not on first paint.** A six-seat thirty-turn episode carries a few
hundred kilobytes of prompt text; turning all of it into DOM nodes before the reader has asked for any of it is
the difference between a page that appears instantly and one that hitches. The `<details>` ships with its
summary and an empty body, and one delegated `toggle` listener fills it the first time it is opened.

**The scrubber** is the transcript's map: one chip per turn, coloured by action type, fabricated turns ringed in
the critical colour, the current turn filled. It is how a reader gets from "something went wrong around the end"
to the turn in one click instead of a scroll hunt.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_TRANSCRIPT` |  |  |
