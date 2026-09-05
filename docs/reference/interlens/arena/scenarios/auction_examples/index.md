# `interlens.arena.scenarios.auction_examples`

The three worked turn views of the auction scaffold, generated from real frozen draws.

`docs/templates/rendered_examples.md` was written by hand before any code existed, so its numbers are
illustrative rather than drawn: its catalogue blurbs vary where a fixed phrase table cannot, and two of its
private blocks omit a line the template file states unconditionally. Reproducing hand-written prose byte for
byte is not a transcription check — it is a check that the transcriber copied the same inconsistencies.

So the relationship is inverted here: these three views are GENERATED from the scaffold over real draws, the
generated text is what `rendered_examples.md` holds, and `tests/test_auction_prompts.py` pins the two
together. Any later edit to the wording, on either side, breaks that test. The narrative message history of
each example is scripted verbatim from the reviewed document, since the message prose is what a reviewer is
actually reading the examples for.

Run `experiments/rational_agents/auction/render_prompt_examples.py` to rewrite the document.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `EXAMPLES` | `tuple[dict, ...]` |  |
| `NARRATIVES` | `dict[str, tuple[tuple, ...]]` |  |

## Functions

| Name | Summary |
|---|---|
| [`build_example`](build_example.md) | Drive one example's episode to its target stage and round, then render `(system, turn)` for its seat. |
| [`render_document`](render_document.md) | The whole `rendered_examples.md` body, generated. |
