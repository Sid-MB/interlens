# `interlens.arena.viz.concepts`

What each solution concept IS, in one place, for every part of the visualizer that explains one to a reader.

A leaf module on purpose: the browser layer (`assets/js_hover`, which serializes :data:`CONCEPT_MATH` straight
into the page's script) and anything rendering an explanation server-side both read THIS, so the axioms cannot
drift into two versions that disagree. `geometry` re-exports :data:`CONCEPT_LABELS`, which is also the legend
order the chart marks them in.

The formulae are HTML — `<sub>` plus Unicode operators (`Σ Π τ − >`) and named entities — rather than LaTeX,
because every page is opened off `file://` with no network: a maths library would either be a CDN request that
leaves the explanation blank or a large vendored blob to typeset five one-line objectives. Notation throughout:
`u_i` is party `i`'s utility for a deal, `tau_i` its walk-away threshold, `b_i` its ideal, and
`z_i = max(u_i - tau_i, 0) / (b_i - tau_i)` the normalized surplus both chart axes are built from.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `AXIS_NOTES` |  |  |
| `CONCEPT_LABELS` |  |  |
| `CONCEPT_MATH` |  |  |
| `PROJECTION_CAVEAT` |  |  |
| `ROLE_NOTES` |  |  |
