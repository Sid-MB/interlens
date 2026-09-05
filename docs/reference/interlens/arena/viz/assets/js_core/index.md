# `interlens.arena.viz.assets.js_core`

Browser layer, part 1: the payload, the formatting helpers, and the deal-detail panel.

Loaded first on every page. Three jobs:

**Rehydration.** Prompt views travel as indices into a de-duplicated message pool rather than as inlined text —
a six-seat episode's thirty turns repeat the same system prompt thirty times and each view re-states the whole
history so far, so the pool is worth roughly a third of the page. :js:func:`viewOf` turns a turn's indices back
into `[{role, content}]` on demand; nothing else in the page knows the difference.

**Formatting.** One escape helper, one number formatter, one signed formatter, one "is this the good direction"
class picker — so a value is never formatted two different ways on two different panels.

**The action grammar.** :js:func:`actKind` maps an action type to the class, glyph, and word the transcript, the
scrubber, and the chart all wear for it. One mapping, so propose is the same blue everywhere it appears.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_CORE` |  |  |
| `JS_UTIL` |  |  |
