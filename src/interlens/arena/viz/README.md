<!-- [rational_agents: viz] 2026-07-29 -->
<!-- [rational_agents: viz-ux] 2026-08-03 — UI/UX overhaul: shell, navigation, keyboard, sortable index, page diet -->

# `interlens.arena.viz` — interactive episode visualizer

The project's shared renderer for negotiation episodes. Point it at any run directory; get one self-contained interactive HTML page per episode, plus a run index. Where [`arena/export.py`](../export.py) answers *what was said*, this answers *was it any good*: every deal placed against the exact Pareto frontier and the axiomatic solution points, every turn's action beside what a rational agent would have done there with the regret between them, and every prompt the models actually saw, expandable and marked with its provenance.

Pages are opened over `file://` — no server, no build step, no network assets of any kind. Light and dark are both explicitly styled, and the top bar's theme toggle stamps the viewer's choice so it wins over the OS setting in either direction.

## Getting around

Every page wears the same shell, so the controls are learned once.

- **Top bar** — the run name (linking back to the index), previous/next page, a picker of every page in the run, and the quick read (outcome, primary, turns, and the fabricated count when there is one). The exporter fills the navigation once the whole run is written, so it only appears on exported sets, not on a single `render_episode` string.
- **Summary strip** — the whole episode in one row above the chart: outcome, primary against its ceiling, distance to the Nash bargaining solution in the chart's own two coordinates, joint welfare, worst-off party, Nash welfare, Gini, parties below threshold, turns, fabricated turns, total regret, and cost when the episode recorded one.
- **Turn scrubber** — one chip per turn under the transcript heading, coloured by what the seat did and ringed in red where the engine fabricated the turn. It is how you get from "something went wrong near the end" to the turn in one click.
- **Keyboard** — `j`/`k` walk the turns, `n`/`p` the episodes, `u` goes up to the index, `f` jumps to the frontier, `t` toggles the chart's numeric table, `e`/`c` expand and collapse every panel, `0` resets the chart zoom, `d` (comparison) jumps to the divergence, `x` (comparison) toggles the counterfactual column, `/` (index) focuses the filter, and `?` opens the help overlay. The overlay is generated from the same binding list the handler reads, so a shortcut cannot exist without being documented. Shortcuts never fire while you are typing, and never shadow a modified keystroke.
- **Index** — a sortable, filterable table rather than a bare list: outcome, primary (with an inline magnitude bar), distance to NBS, USW, worst-off, fabricated share, arm, seed, instance and total regret, with a text filter and deal / no-deal / has-fabricated-turns chips. Sorting reads a `data-sort` value off each cell, so it sorts on the number and sinks missing values; there is no second JSON copy of the rows, and every number is present with scripting off.

## Page weight

Prompt views travel as indices into one de-duplicated message pool (`msgpool`), rebuilt in the browser on demand: a six-seat episode repeats its system prompt on every turn and each view re-states the whole history, so the same bytes were shipping dozens of times. Prompt panel *bodies* are also built on first open rather than first paint, which is most of the DOM a long episode would otherwise construct before showing anything. Measured over three demo sets (28 comparable pages), total weight fell 6.88 MB → 5.48 MB (−20%); the pages that actually hurt fell hardest — the largest episode page 660 KB → 456 KB (−31%), the largest comparison page 1098 KB → 635 KB (−42%). Small pages gain ~28 KB, the fixed cost of the shared stylesheet and browser layer.

## Quick start

```bash
# one page per episode of a run, plus index.html and manifest.json
python -m interlens.arena.viz --run /nlp/scr/$USER/ii_mats/rational_agents/p2_pilot_qwen3_4b_v2 \
                              --out .claude/products/episode_viz/pilot --limit 3

# seat-swap comparison: same instance + seed, one seat's occupant swapped
python -m interlens.arena.viz --compare RUN_all_llm RUN_mixed \
                              --out .claude/products/episode_viz/seatswap --limit 4 --select deal-flip

# your browser is not on the machine holding the run: render to a temp dir and serve it
python -m interlens.arena.viz --run RUN_DIR --limit 5 --serve
```

`--out` is optional — without it the pages go to a fresh `$TMPDIR/interlens_viz_*` whose path is printed. `--serve` then hosts that directory over HTTP until Ctrl-C, printing the URL and the `ssh -L` command to forward the port (ephemeral by default; `--port N` to pin it). Every flag is documented in `--help`. From Python:

```python
from interlens.arena import viz

viz.export_run(run_dir, out_dir, limit=3)                    # pages + index, returns a manifest
viz.export_comparison(left_run, right_run, out_dir, select="largest-effect")
html = viz.render_episode(run_dir, episode_json_path)        # the HTML as a string, nothing written
payload = viz.RunDir(run_dir).payload(episode_json_path)     # every number the page shows, as a dict
viz.serve_directory(out_dir, port=0)                         # serve rendered pages until KeyboardInterrupt
```

## What a run directory needs

| Path | Needed for | Missing? |
|---|---|---|
| `episodes/` | everything | required (a bare episodes dir also works as `--run`) |
| `instances/` | the frontier, thresholds, solution points, per-party surplus | page renders transcript only, with a notice |
| `annotations/` | post-hoc oracles, above all `bestresponse` | the counterfactual column says so instead of being blank |
| `manifest.json` | which seats were LLMs vs computable policies | inferred from output-token accounting, and labelled as inferred |

## The frontier chart

With six parties a deal's utility vector has six dimensions, so there is no honest utility-space scatter. The chart projects the exact `|D| x n` surplus table onto the two axes that carry the normative content, both in scale-invariant normalized-surplus coordinates:

- **x — joint welfare**: mean normalized surplus. The utilitarian axis.
- **y — worst-off party**: minimum normalized surplus. The egalitarian axis, and exactly what discrete Kalai-Smorodinsky maximizes.

Up and to the right is better for everyone, so the frontier's image is the upper-right envelope. Marked on it: the play trajectory as numbered points, the deal that closed, the oracle's recommendation at each turn, the five solution concepts (NBS, KS, utilitarian, egalitarian, MNW), and each party's individually-best efficient deal.

Hovering anywhere on the chart opens the **nearest** deal — every one of the `|D|` deals is inspectable this way, not only the marked ones. Disclosure is progressive: a hover gives the headline read (what the deal is, its joint welfare and worst-off party, whether it is efficient and whether it can close), and **clicking pins** the full per-party breakdown — utility, threshold, surplus, and share of that party's ideal — which then survives an accidental pointer sweep. A marked deal keeps its own richer titled hover; clicking a numbered move also selects that turn in the transcript, and selecting a turn rings the deal it put on the chart, so the sync runs both ways.

The chart zooms and pans in plain SVG: drag to pan, Ctrl/⌘ or Shift with the wheel to zoom (an ungated wheel would hijack page scrolling), the `+`/`−`/`reset` buttons in the corner, double-click or `0` to reset. The nearest-deal maths reads the *current* `viewBox`, and the hover snap radius is a constant number of screen pixels, so zooming in genuinely separates deals that overlap at full extent.

The projection is lossy on purpose, and the code never uses it to decide anything: whether a deal is Pareto-optimal always comes from the exact `pareto_mask`, never from its position on the chart. A deal can therefore sit strictly inside the drawn envelope while being genuinely efficient.

## Colour

Categorical identity is capped at **three** slots, which is the binding all-pairs constraint of the colour formula for a scatter (validated in both modes with `dataviz/scripts/validate_palette.js --pairs all`: worst all-pairs CVD ΔE 9.2 light / 9.4 dark, normal-vision 24.0 / 20.9). Slot 1 is what the model did (or the left episode), slot 2 the oracle's recommendation (or the right episode), slot 3 the normative solution points. Everything else is **shape plus a direct label**: solution concepts share one colour and are each labelled on the chart, per-party ideals share one diamond, and deals themselves are chart chrome rather than a series. Slot 3 falls below 3:1 on the light surface, so the relief rule applies — hence the always-visible labels and the numeric table view that ships with every chart.

Action types in the transcript are **states, not a series**, so they wear the reserved status palette rather than a categorical slot — propose in slot 1 (the same blue its trajectory wears on the chart), accept `good`, reject `serious`, walk `critical`, vote slot 3, talk muted. Every one carries a glyph and a word beside the colour on the card, the scrubber chip, and the turn header, so nothing is ever colour-alone; a computable-policy seat additionally gets a dashed left edge.

## Prompt provenance

Auditing what a model saw only means something if the page is honest about where the text came from. Three states, each labelled in place:

- **stored** — the exact view recorded at generation time (`TurnRecord.view`).
- **reconstructed** — re-derived by deterministic replay through the scenario state machine, because the episode predates view capture. Byte-exact for the state, but rendered by *today's* prompt code.
- **reconstructed_pre_retry** — as above, on a turn that was a retry after a malformed response. Replay re-issues the original request, so this is the **first attempt's** prompt; the repair instruction the model actually saw on the retry is not recoverable from the record. Marked separately so a prompt audit can see which panels are known-incomplete.

`--no-reconstruct-views` disables reconstruction entirely, which is what you want when the pages must contain only bytes that were genuinely recorded.

## Annotation vintage

The per-turn rational-agent counterfactual (and its regret) is read from a run's annotation store. `--annotations-dir NAME` selects WHICH one: the default `annotations` is the original scoring pass, and a re-annotated set such as `annotations_v1` (written by the oracle seat-binding fix) carries the corrected best-response values. The Python API takes the same knob as `annotations_dirname=` on `RunDir`, `export_run`, `export_comparison`, `render_episode`, and `render_compare`. The chosen vintage is stated in a provenance line above the transcript, so a reader always knows which counterfactual they are auditing; a name that does not exist simply yields no counterfactual (reported as missing) rather than an error.

## Seat-swap comparison

Pairs episodes on `(instance_id, seed, arm, cell)` — a key, not a heuristic; an unmatched episode is reported, never approximately matched. The page opens with a **verdict strip** — which side won, on how many metrics, and the largest move in each direction, using each metric's own better-direction so a lower Gini counts as a win for whoever lowered it, and stating the ties rather than dropping them. Below it: a table of paired deltas (right minus left), one shared frontier carrying both trajectories, and two synchronized transcript columns with the first behavioural divergence marked. Each column renders with its own element-id prefix (`lturn-` / `rturn-`), because both sides number their turns from zero and a single prefix put duplicate ids on one page. The columns show each turn's action by default; a **Show each turn's rational-agent counterfactual** toggle adds the per-turn oracle column (what a rational agent would have done, with the regret) inside each side — off by default because the seat swap is itself the rational-vs-LLM contrast.

Turn slots are aligned on `(round, phase, seat)`, and after the divergence point the columns are deliberately presented as two independent trajectories rather than a line-by-line diff: from there on the two episodes are in different states, so the seats are answering different questions and a per-turn "diff" would be meaningless. Divergence is judged on *public* behaviour only (action, deal, offer, message) — two occupants that made the same move have not diverged just because one of them was a policy with no scratchpad to record.

Where several seats were swapped at once (a `mixed` table against `all_llm` replaces every seat but one), focal metrics are the **mean over the whole swapped set**, labelled with its size, because attributing the effect to any single one of those seats would be wrong.

`--select` decides which pairs a `--limit` keeps: `first` (arbitrary), `largest-effect`, or `deal-flip`. Ranking reads only stored outcomes, so it is free over hundreds of pairs. Prefer it to `first` for spot checks — a small `first` sample can easily be all no-deal-on-both and show nothing.

## Layout

| Module | Responsibility |
|---|---|
| `geometry.py` | the exact plottable geometry of one instance: frontier, solutions, party ideals, 2-D embedding |
| `episode.py` | episode + instance + annotation + manifest → one render payload; seat kinds; view provenance |
| `compare.py` | pairing, slot alignment, divergence, focal seats, the score table |
| `chrome.py` | the shell shared by all three page kinds: top bar, nav slot, help overlay, summary strip, and `slim_payload` (the pooled wire form) |
| `page.py` | pure `payload -> HTML`; renders every number server-side |
| `assets/` | the inline stylesheet and browser layer, split by job (see below) |
| `export.py` | the file-writing layer: pages, indexes, manifests, and the nav pass that links each page to its siblings |
| `serve.py` | `--serve`: a stdlib threading HTTP server over an output directory, plus the port-forward banner |
| `__main__.py` | the CLI |

Inside `assets/`: `css.py` (the design system — tokens, light/dark, the action grammar, layout), `js_core.py` (`JS_UTIL` formatting/DOM helpers plus `JS_CORE`, the payload and view rehydration), `js_chart.py` (frontier chart with hover/pin/zoom, regret strip), `js_transcript.py` (turn cards, scrubber, lazy prompt bodies, turn selection), `js_shell.py` (theme, navigation, keyboard, help), and one wiring module per page kind (`js_episode.py`, `js_compare.py`, `js_index.py`). The index loads only the helpers and the shell, since it carries no episode payload.

The split keeps `page.py` testable without a filesystem and `geometry.py`/`compare.py` testable without HTML. Because every number is rendered in Python and only the charts and transcript cards are drawn in the browser, [`tests/test_arena_viz.py`](../../../../../tests/test_arena_viz.py) asserts on real structure and real values with no browser involved (57 tests, including a `node --check` parse gate on all three page kinds' emitted scripts). The demo sets are additionally executed page by page in a real DOM before release.
