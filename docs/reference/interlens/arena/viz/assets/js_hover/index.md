# `js_hover`

Module `interlens.arena.viz.assets.js_hover`

Browser layer, part 2a: the rich hover card that EVERY point on the frontier chart carries.

The chart plots the whole deal space, so a reader hovering a dot is asking three questions at once — *what am I
looking at*, *what deal is it*, and *who does it favour*. Before this the answer was a one-line SVG `<title>`
plus a panel far below the chart, so identifying a point meant looking away from it. The card answers all three
at the pointer:

1. **What it is.** Role-specific phrasing: a solution concept, a party's dictated best, an oracle's move at a
   turn, a numbered move by a seat, the deal that closed, or an ordinary point in the cloud.
2. **The deal**, in words — `Location: Kestrel Park · Power: solar with storage` — decoded client-side from the
   deal index against the issue/option name table the game payload already ships, so no per-deal strings travel.
3. **The numbers**: the deal-level summary (mean and min normalized surplus, Nash welfare, distance below the
   frontier, IR and feasibility flags) and a compact per-party table sorted by normalized surplus — the "who
   wins most here" ranking, with each party's utility, threshold, raw surplus and a bar.

**The maths is written out, without a maths library.** The five solution concepts are definitions, not labels, so
each carries its formula and the one property that distinguishes it (Nash's axioms, KS's monotonicity,
utilitarianism's *lack* of scale invariance, egalitarian maximin, MNW's Caragiannis fallback). Those definitions
live in :mod:`interlens.arena.viz.concepts` and are serialized into the page from there, so a second place that
explains a concept to a reader cannot disagree with this one. Pages are opened off `file://` with no network, so
the formulae are HTML `<sub>` plus Unicode operators (`Σ Π τ − >`) rather than KaTeX or MathJax — they render
everywhere, add nothing to the page weight, and copy as readable text.

**One card, never under the cursor.** A single element is reused for every point on the page, so two cards can
never be open at once; it is offset from the pointer and flips side or vertical anchor near a viewport edge. A
click *pins* it (the card becomes interactive and stays put until the next pick or `Escape`), which is also
what makes it usable by touch, where there is no hover. Everything is styled from the shared CSS variables, so
it follows the light/dark theme like the rest of the page.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_HOVER` |  |  |
