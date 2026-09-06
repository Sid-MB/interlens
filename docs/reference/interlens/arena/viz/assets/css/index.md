# `css`

Module `interlens.arena.viz.assets.css`

The one stylesheet every page wears — a small design system, inlined.

Three things make this a system rather than a pile of rules:

**Tokens, in one place.** Colour, spacing (`--sp-*`), type scale (`--t-*`) and radii are custom properties
declared once. Light is the default declaration; dark is *selected* — the same roles re-stated for the dark
surface under BOTH the OS media query and an explicit `data-theme` scope, so the page's own theme toggle wins in
either direction rather than only being able to follow the OS.

**Categorical colour is capped at three** (`--s1`/`--s2`/`--s3`), the binding all-pairs constraint for a
scatter; everything else is shape, position, or the reserved status palette. Action types on the transcript wear
status colours (accept = good, reject = serious, walk = critical) because they are *states*, never a series — and
each one ships with a glyph and a word, so colour never carries the meaning alone.

**Nothing is decorative.** Borders are hairlines, grid and axis ink is recessive, and the only heavy weights on the
page are the numbers a reader came for.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `CSS` |  |  |
