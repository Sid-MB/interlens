# `interlens.arena.live.style`

The rules the lobby and the play page both need: form controls, seat cards, and the two docks.

Live play is the only part of the visualizer with FORMS in it — everything else renders numbers and prose — so
the shared stylesheet (`viz.assets.CSS`) styles no input, select or textarea, and both live pages would
otherwise carry their own copy of the same handful of rules. They are here instead, in the vocabulary of the
shared sheet's own tokens (`--surface-1`, `--ring`, `--sp-3`), so a live control looks like part of the
same page as the transcript beside it and a change to either page's controls is one edit rather than two.

Page-specific layout stays on the page that owns it (the lobby's start bar and problem lists, for instance);
what is here is what a seat card, a labelled field and a dock are on both.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `CSS_LIVE` |  |  |
