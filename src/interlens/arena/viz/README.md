<!-- [rational_agents: viz] 2026-07-29 -->
<!-- [rational_agents: viz-ux] 2026-08-03 — UI/UX overhaul: shell, navigation, keyboard, sortable index, page diet -->
<!-- [rational_agents: viz-sidebar] 2026-08-03 — the tabbed, scroll-synced sidebar -->
<!-- [rational_agents: viz-hovers] 2026-08-03 — rich hover cards on every chart point, with the solution-concept definitions -->
<!-- [rational_agents: viz-upgrades] 2026-08-12 — four-type decision references with per-type units, run hazard badges, the silent-turn census, the final-vote tally -->

# `interlens.arena.viz` — interactive episode visualizer

The project's shared renderer for negotiation episodes. Point it at any run directory; get one self-contained interactive HTML page per episode, plus a run index. Where [`arena/export.py`](../export.py) answers *what was said*, this answers *was it any good*: every deal placed against the exact Pareto frontier and the axiomatic solution points, every turn's action beside the post-hoc oracle counterfactual and its value gap, and every prompt the models actually saw, expandable and marked with its provenance.

Pages are opened over `file://` — no server, no build step, no network assets of any kind. Light and dark are both explicitly styled, and the top bar's theme toggle stamps the viewer's choice so it wins over the OS setting in either direction.

## Getting around

Every page wears the same shell, so the controls are learned once.

- **Top bar** — the run name (linking back to the index), previous/next page, a picker of every page in the run, and the quick read (outcome, primary, turns, and the fabricated count when there is one). The exporter fills the navigation once the whole run is written, so it only appears on exported sets, not on a single `render_episode` string.
- **Summary strip** — the whole episode in one row above the chart: outcome, primary against its ceiling, distance to the Nash bargaining solution in the chart's own two coordinates, joint welfare, worst-off party, Nash welfare, Gini, parties below threshold, turns, fabricated turns, total regret, and cost when the episode recorded one.
- **Turn scrubber** — one chip per turn under the transcript heading, coloured by what the seat did and ringed in red where the engine fabricated the turn. It is how you get from "something went wrong near the end" to the turn in one click.
- **Sidebar** — five tabs on the right, three of which follow the transcript as you scroll (see below).
- **Keyboard** — `j`/`k` walk the turns, `n`/`p` the episodes, `u` goes up to the index, `f` jumps to the frontier, `t` toggles the chart's numeric table, `s` cycles the sidebar tabs, `e`/`c` expand and collapse every panel, `0` resets the chart zoom, `d` (comparison) jumps to the divergence, `x` (comparison) toggles the counterfactual column, `/` (index) focuses the filter, and `?` opens the help overlay. The overlay is generated from the same binding list the handler reads, so a shortcut cannot exist without being documented. Shortcuts never fire while you are typing, and never shadow a modified keystroke.
- **Index** — a sortable, filterable table rather than a bare list: outcome, preference visibility (`PRIVATE` or `FULL`), parameter difficulty and tags, primary (with an inline magnitude bar), distance to NBS, USW, worst-off, score differential, fabricated share, arm, seed, instance and total regret, with a text filter and deal / no-deal / has-fabricated-turns chips. A comparison index with at least three non-constant difficulty/effect pairs reports Pearson's difficulty × score-differential correlation and its sample count. Sorting reads a `data-sort` value off each cell, so it sorts on the number and sinks missing values; there is no second JSON copy of the rows, and every number is present with scripting off.

## The sidebar

The episode page's right-hand column is five tabs over one sticky pane. The first is the game panel the page always had; three live views answer the same question — *what did the table look like at the point in the transcript I am reading?* — and are kept in sync by one `IntersectionObserver` over the turn cards (not a scroll handler: the browser does the geometry, and there is no per-frame work). The topmost card in the viewport is the turn in view, and its seat is the acting seat. The final Info tab is a standing reading guide.

- **Game info** — who is at the table, thresholds, protocol, problem size, every private score sheet, prompt provenance.
- **Preference visibility** — a public/full-information episode is called out at the top of the page and in the sticky quick read because every party saw every score sheet and threshold. Private information is the default and adds no banner.
- **Conversation** — the public chat from the acting seat's point of view: that seat's bubbles on the right, everyone else's on the left with the speaker named, and the list scrolls itself so the turn you are reading stays in the middle. Each bubble's CONTENT is **only what was actually published** — the free-text message and the formal move as a compact chip (`PROPOSE P3: Cooling=air cooling, …`, `ACCEPT P2`, `WALK`; a talk-only turn has no chip). Scratchpads, prompts, and oracle verdicts are private or post-hoc and are deliberately absent, as are the first attempts at a retried turn, which the engine never published to anyone. The exceptions are three provenance badges, none of which the table saw and each of which is marked as an annotation rather than set in the body: `NOT GENERATED`, `SAID NOTHING`, and — on a live-played episode — who held the seat, when a person played the turn or the seat had changed hands. They earn their place because omitting them misleads in the other direction: an engine placeholder reads as a deliberate pass, and a seat that changed hands reads as one continuous player. Turns after the one in view are dimmed rather than hidden.
- **Frontier** — the same chart, drawn by the same `frontierChart`, restricted in time: proposals up to the turn in view are numbered, the deal standing on the table is squared, later ones are ghosted. Clicking a move selects that turn in the transcript. Every transcript package link opens a large hover/focus preview built with `frontierChart`. Current dual-reference annotations plot all three decisions at once: the package actually proposed or considered (circle), the rational policy using only the acting seat's private information (diamond), and the omniscient oracle using every hidden sheet (square). Older `bestresponse` annotations retain the two-way proposal/accept/reject preview. Activate any package link to pin the preview on keyboard or touch; Escape dismisses it. Inside the preview the deal cloud recedes further than on the main chart while staying drawn — the labelled points mean nothing without the space they sit in — and the envelope is left alone, because it is what orients the reader.

A declined offer also gets a one-line rationale above its package, explaining that the reference is holding out for the specific package shown below it. An **accept** recommendation deliberately gets none: its deal is the offer already standing, so there is no alternative package for a "because" to point at, and inventing one would attribute to the oracle a comparison it never made. The branch reads the stored action kind (`best_atype`), not the formatted label.
- **Issues** — the acting seat's own valuation, one vertical bar per issue on that agent's score scale. Each option is a tick (named on hover only — a label per option per issue is unreadable at sidebar width), the deal on the table marks the option it picks on every bar, and one horizontal line crosses the whole chart at **threshold / n_issues**: the average per-issue score that agent needs to clear. Under it: the deal's total for this agent, the threshold, the surplus, and a z against every deal in the space. The picker pins a seat; the next time scrolling changes the turn in view, the pin is released and the tab goes back to following the acting seat.
- **Info** — how the oracle scores legal candidate actions and computes its nonnegative improvement gap, plus a compact guide to utilities, thresholds, normalized surplus, the frontier, public-vs-private views, annotation provenance, and generation-failure placeholders. On a PRIVATE episode it states prominently that the standard saved `bestresponse` annotation is omniscient: it uses every hidden sheet and threshold, so its recommendation is a hindsight diagnostic rather than an implementable policy. Circular information buttons beside oracle measurements open this tab directly at the oracle explanation.

The offer ids the chips quote (`ACCEPT P2`) and the deal standing on the table are **reconstructed** in `episode.py` (`public_ledger`) rather than in the browser, because `OfferRegistry` mints ids sequentially over published proposals and no stored record keeps the proposer's side of that. Everything but the two charts and the moving markers renders server-side, so the sidebar still reads with scripting off — it simply stops following the scroll.

On a private-information episode the issue tab says so in as many words: the viewer is post-hoc and omniscient, and no seat could see another's sheet while playing.

## Page weight

Prompt views travel as indices into one de-duplicated message pool (`msgpool`), rebuilt in the browser on demand: a six-seat episode repeats its system prompt on every turn and each view re-states the whole history, so the same bytes were shipping dozens of times. Prompt panel *bodies* are also built on first open rather than first paint, which is most of the DOM a long episode would otherwise construct before showing anything. Measured over three demo sets (28 comparable pages), total weight fell 6.88 MB → 5.48 MB (−20%); the pages that actually hurt fell hardest — the largest episode page 660 KB → 456 KB (−31%), the largest comparison page 1098 KB → 635 KB (−42%). Small pages gain ~28 KB, the fixed cost of the shared stylesheet and browser layer.

The sidebar spends some of that back, on purpose: on a six-seat five-issue page it adds ~58 KB (a 558 KB page), 18 KB of chat bubbles and 39 KB of per-seat issue charts. That is the cost of rendering them server-side — six seats' bars are drawn whether or not a reader opens the tab — and it buys a sidebar that works with scripting off and numbers the tests can assert without a browser.

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
| `README.md` | optional run description above the index table | omitted; the index starts with the table |
| `VINTAGE_PROVENANCE.md` | the hazard banner and index tag marking a run whose agents carry a known defect | no hazard is claimed, which is the healthy case |
| `vote_derivation.json` | the final-vote tally's *derived ballot* column (written by gate G3 with `--viz-sidecar`) | the recorded ballots are tabulated alone, and the page says how to fill the column |

The run README is rendered as CommonMark with embedded HTML disabled, so rollout documentation can explain the
campaign and its caveats without becoming executable page content. It is included by `--run`; a `--compare`
index does not choose between or combine the two source runs' READMEs.

## The frontier chart

With six parties a deal's utility vector has six dimensions, so there is no honest utility-space scatter. The chart projects the exact `|D| x n` surplus table onto the two axes that carry the normative content, both in scale-invariant normalized-surplus coordinates:

- **x — joint welfare**: mean normalized surplus. The utilitarian axis.
- **y — worst-off party**: minimum normalized surplus. The egalitarian axis, and exactly what discrete Kalai-Smorodinsky maximizes.

Up and to the right is better for everyone, so the frontier's image is the upper-right envelope. Marked on it: the play trajectory as numbered points, the deal that closed, the oracle's recommendation at each turn, the five solution concepts (NBS, KS, utilitarian, egalitarian, MNW), and each party's individually-best efficient deal.

**Efficient is not the same as reachable, and the cloud says so in three tiers.** Being Pareto-optimal answers "is any value wasted"; it does not answer "would anyone sign this". A deal can be on the frontier while leaving some party below its threshold — typically in the bottom-right corner, where joint welfare is maximized precisely *by* pushing somebody under — and no such deal can close. So the ringed frontier and the shaded region are the **IR-feasible** frontier, `pareto & ir` (`GameGeometry.pareto_ir`, shipped to the browser as `deals.pareto_ir` and `envelope_ir`); a deal that is efficient but below a party's threshold is drawn as a muted **cross** with its own legend entry and its own hover wording, and the unconstrained Pareto staircase remains on the chart as a dashed line where it runs outside the reachable one. Nothing is dropped and nothing is recomputed: `pareto_mask` and the `d_frontier` metric are untouched (that distance is still measured to the *unconstrained* frontier, which the frontier pill's tooltip states), and `pareto_ir` is purely derived — this was a presentation bug, in which one styling was asserting two different facts.

Hovering anywhere on the chart opens the **nearest** deal — every one of the `|D|` deals is inspectable this way, not only the marked ones. Below the chart, disclosure is progressive: a hover gives the side panel's headline read (what the deal is, its joint welfare and worst-off party, whether it is efficient and whether it can close), and **clicking pins** the full per-party breakdown, which then survives an accidental pointer sweep. Clicking a numbered move also selects that turn in the transcript, and selecting a turn rings the deal it put on the chart, so the sync runs both ways.

A semantic marker replaces that deal's anonymous cloud dot or frontier ring, including in nearest-deal hit
testing, so one deal cannot alternate between an unnamed and a named hover identity. Multiple meaningful markers
are preserved: when a played blue proposal is also a green party-best deal, the blue circle is layered below the
diamond so both facts remain visible and each marker remains focusable and hoverable. Every party-best diamond
also carries the party's name in a tiny direct label; party-specific label anchors keep the names separate when
several parties share the same best deal.

### Hover cards

At the pointer, **every** point — cloud dot, frontier ring, solution star, party-best diamond, oracle circle, numbered move, the AGREED square, the sidebar's standing offer — opens the same rich card (`assets/js_hover.py`), because a reader pointing at a dot is asking three questions at once and looking away from the chart to answer them loses the point they were pointing at. Four blocks, every time:

1. **What it is**, phrased per role: which solution concept, whose dictated best, which turn's oracle move, which numbered move by which seat, the deal that closed.
2. **The deal in words** — `Location: Anvil Ridge · Power supply: solar with storage · …`, decoded in the browser from the deal index against the one issue/option name table the payload already ships. `|D| x n_issues` option strings would be most of the page; integers plus a name table are nothing.
3. **The numbers**: mean and worst-off normalized surplus, Nash welfare (the geometric mean of the `z`s, and so zero the moment anyone is left below threshold), distance below the frontier, and the IR / can-close flags.
4. **"Who wins most here"** — every party ranked by normalized surplus, with the utility, threshold, raw surplus and a bar the ranking is a summary *of*.

A special point additionally carries **its definition**: the objective it maximizes and the one property that separates it from its neighbours — Nash's four axioms, KS's monotonicity, the utilitarian point's *lack* of scale invariance, egalitarian maximin, MNW's Caragiannis fallback for an empty strict-IR problem. Scale invariance is read off the stored solution record rather than hardcoded, so a concept the solver marks as scale-dependent always says so. The formulae are HTML `<sub>` plus Unicode operators (`Σ Π τ − ≥`), not a maths library: a CDN request would leave the card blank on `file://`, and vendoring KaTeX to typeset five one-line objectives is not a trade worth making.

**Points that happened are clickable; points that are properties of the game are not.** A numbered move, an oracle circle and the AGREED square each stand for a real event, so clicking one jumps the transcript to that turn and flashes the destination card — a smooth scroll that ends among thirty near-identical cards otherwise leaves a reader unsure which one they were sent to. The card also carries an explicit `go to turn N →` button, so the jump is discoverable and works on touch, where there is no hover. A solution star, a party-best diamond and an ordinary cloud deal have no event behind them: clicking those pins the card and moves nothing. The distinction is one list (`EVENT_ROLES`) and is visible in the rendered marks as a `data-markturn` anchor, so it cannot silently invert. `turn-<idx>` is the id contract, the same one `makeSelectTurn`, the scrubber chips and the regret bars use. The AGREED square is the one mark that stands for an event without naming its turn, so the closing turn is derived server-side by `episode.closing_turn_index` — the last published closing action (accept, or a vote ballot) taken while the agreed deal was the one standing — and shipped as `outcome.closing_turn_idx`.

**Both axis titles carry an info control** (a focusable circled *i* drawn in the SVG) opening the same card: what `z_i` is, what the axis does with it, why it is scale-invariant, and — on both — the standing caveat that the chart is a 2-D projection of the full `n`-dimensional `z`-space, so two deals can share a point and on-screen closeness is a guide rather than a measurement (the exact distances are in the numeric table under the chart). The wording lives beside the concept definitions in `concepts.py` (`AXIS_NOTES`, `PROJECTION_CAVEAT`).

There is one card element per page, shared by the main chart and the sidebar's mini chart, so two can never be open at once. It is offset from the pointer and flips side near a viewport edge rather than overlapping the mark; while un-pinned it takes no pointer events (a card that could would eat the hover keeping it open); a click **pins** it, which is also how it is read on touch, where there is no hover; `Escape` dismisses it. Marks no longer carry an SVG `<title>` — the native tooltip would land on top of the card a second later saying less — but keep their accessible name and keyboard focus, and focusing a mark opens its card anchored to the mark itself.

The chart zooms and pans in plain SVG: drag to pan, Ctrl/⌘ or Shift with the wheel to zoom (an ungated wheel would hijack page scrolling), the `+`/`−`/`reset` buttons in the corner, double-click or `0` to reset. The nearest-deal maths reads the *current* `viewBox`, and the hover snap radius is a constant number of screen pixels, so zooming in genuinely separates deals that overlap at full extent.

The projection is lossy on purpose, and the code never uses it to decide anything: whether a deal is Pareto-optimal always comes from the exact `pareto_mask`, never from its position on the chart. A deal can therefore sit strictly inside the drawn envelope while being genuinely efficient.

## Colour

Categorical identity is capped at **three** slots, which is the binding all-pairs constraint of the colour formula for a scatter (validated in both modes with `dataviz/scripts/validate_palette.js --pairs all`: worst all-pairs CVD ΔE 9.2 light / 9.4 dark, normal-vision 24.0 / 20.9). Slot 1 is what the model did (or the left episode), slot 2 the oracle's recommendation (or the right episode), slot 3 the normative solution points. Shape and direct labels distinguish the references within that family: NBS, KS, and EGAL are green stars; UTIL and MNW are violet triangles; per-party ideals are green diamonds. The violet is a redundant reference-point accent, not a fourth trajectory identity—the triangle and direct `UTIL` / `MNW` labels carry the distinction without colour. Deals themselves are chart chrome rather than a series. Slot 3 falls below 3:1 on the light surface, so the relief rule applies — hence the always-visible labels and the numeric table view that ships with every chart.

The sidebar's charts spend no new slots. A proposal the reader has not scrolled to yet is the *same* series at a different time, so it is ghosted by weight (opacity and size) and keeps slot 1 — a fourth hue for "later" measured ΔE 2.0 against slot 3 under deuteranopia, i.e. indistinguishable from the solution stars. The issue bars carry one encoded identity (the deal on the table, slot 1) against chrome: option ticks and the τ/n_issues line are ink, and the three are told apart by weight and dash as well as colour, each named in the legend under the chart and on hover.

Action types in the transcript are **states, not a series**, so they wear the reserved status palette rather than a categorical slot — propose in slot 1 (the same blue its trajectory wears on the chart), accept `good`, reject `serious`, walk `critical`, vote slot 3, talk muted. Every one carries a glyph and a word beside the colour on the card, the scrubber chip, and the turn header, so nothing is ever colour-alone; a computable-policy seat additionally gets a dashed left edge.

## Prompt provenance

Auditing what a model saw only means something if the page is honest about where the text came from. Three states, each labelled in place:

- **stored** — the exact view recorded at generation time (`TurnRecord.view`).
- **reconstructed** — re-derived by deterministic replay through the scenario state machine, because the episode predates view capture. Byte-exact for the state, but rendered by *today's* prompt code.
- **reconstructed_pre_retry** — as above, on a turn that was a retry after a malformed response. Replay re-issues the original request, so this is the **first attempt's** prompt; the repair instruction the model actually saw on the retry is not recoverable from the record. Marked separately so a prompt audit can see which panels are known-incomplete.

`--no-reconstruct-views` disables reconstruction entirely, which is what you want when the pages must contain only bytes that were genuinely recorded.

## Scratchpad provenance

The scratchpad renders inline above the public message, in recessive grey, capped at a scroll height rather than truncated — an ellipsis in a scratchpad is a claim about the reasoning the record does not support. Its header names **what kind of record the text is**, because the stored token alone does not say: `full` and `withheld_or_summarized` are internal spellings, and the two most common cases on a hosted provider look identical without this distinction.

- **verbatim chain of thought** (`full`) — the complete reasoning stream as the provider returned it.
- **provider summary — the raw chain of thought was not returned** (`withheld_or_summarized`) — the model reasoned, but only a summary or redacted blocks came back.
- **elicited rationale** — prose the *scaffold asked for* in the response body (`parsed_action.thinking`), not a reasoning stream at all. This wins over the provider token, which is about a different channel: a turn whose thinking stream was withheld while the scaffold's rationale arrived normally is an elicited rationale, and labelling it as a provider summary would describe text that is present as text that is missing.

An unrecognized token renders as itself, so a future provenance value is never described wrongly. `reasoning_source` on each turn payload (`elicited` / `provider` / `none`) is what the distinction reads.

## Annotation vintage

The per-turn post-hoc oracle counterfactual (and its improvement gap, traditionally called regret) is read from a run's annotation store. For a model action `a_t` and the oracle's best scored legal action `a*_t`, the gap is `V_t(a*_t) - V_t(a_t) >= 0`. The standard `bestresponse` annotation uses the full game table. In PRIVATE games it therefore sees every party's hidden sheet and threshold: the gap is omniscient hindsight regret, not regret against a policy available to the acting seat. The model's oracle-scored value is shown with **The model acted**; the best value and positive **value improvement available** stay with the oracle's counterfactual. `--annotations-dir NAME` selects WHICH annotation set is used: the default `annotations` is the original scoring pass, and a re-annotated set such as `annotations_v1` (written by the oracle seat-binding fix) carries the corrected best-response values. The Python API takes the same knob as `annotations_dirname=` on `RunDir`, `export_run`, `export_comparison`, `render_episode`, and `render_compare`. The chosen vintage is stated in a provenance line above the transcript, so a reader always knows which counterfactual they are auditing; a name that does not exist simply yields no counterfactual (reported as missing) rather than an error.

## Decision references: four of them, on two axes, in two units

Current campaign annotations store direct decision references on each `TurnAnnotation`. The
`five-seat-triple-counterfactuals-v1` schema stores **four**, which is one point in a 2x2 — *information* across
(what the reference could see) and *objective* down (what it was maximizing):

|  | private | omniscient |
|---|---|---|
| **self-interest** | `rational_private` | `oracle_omniscient` |
| **table fairness** | `fairness_private` | `fairness_oracle` |

```json
{
  "turn_idx": 4,
  "counterfactuals": {
    "rational_private":  {"action": {"action": "propose"}, "deal_index": 17, "value": 4.27,
                          "information": "own_private_sheet+public_actions_only"},
    "oracle_omniscient": {"action": {"action": "propose"}, "deal_index": 53, "value": 37.0,
                          "information": "all_private_sheets+public_actions"},
    "fairness_private":  {"action": {"action": "propose"}, "deal_index": 165, "value": 0.8795,
                          "table_optimum": 1.1409, "own_surplus": 63.0,
                          "information": "own_private_sheet+public_actions_only"},
    "fairness_oracle":   {"action": {"action": "propose"}, "deal_index": 53, "value": 1.1409,
                          "table_optimum": 1.1409, "own_surplus": 37.0,
                          "information": "all_private_sheets+public_actions"}
  }
}
```

**`value` does not mean the same thing on the two rows, and this is the page's central labelling job.** A
self-interest row's `value` is in the acting seat's own score-sheet points. A fairness row's `value` is the
*table* objective — a smoothed log-Nash score over normalized surplus, belonging to the whole table and to no
seat, on an entirely different scale, bounded by the `table_optimum` recorded beside it. The seat's own points at
that same deal are the separate `own_surplus` field, and a fairness reference will happily give those away, which
is the point of the reference. Two readers auditing these records by hand have already subtracted the wrong pair.

So [`references.py`](references.py) owns the 2x2 and every unit string, the payload carries the unit *with* each
value, and the page renders all four in one grid whose row headers state their units and whose footer says which
numbers may be subtracted from which. The subtler half: the two fairness values are both priced on the same true
full-information objective, so their difference IS a measurement (what deciding blind costs the table) — while
the two self-interest values share a unit without being the same quantity (the private one is an expectation
under the seat's posterior, the omniscient one is exact on the true tables), so their difference measures
nothing. The payload says which is which as `comparable_across_information`.

`deal` may replace `deal_index`; the visualizer resolves a named deal through the instance's exact deal space.
Aliases from early campaign prototypes (`private_rational`, `omniscient_oracle`, `fairness_rational`, and related
short forms) are normalized at load time. A dual-schema (two-reference) annotation renders one objective row and
says the fairness row is absent; annotations with no `counterfactuals` at all retain their existing
`bestresponse` display and draw no grid.

## Run hazards: vintage and generation budget

Two facts decide whether a run's numbers may be compared with another run's, both properties of the RUN rather
than the episode, and both invisible on the pages for as long as they existed.

**Vintage.** A `VINTAGE_PROVENANCE.md` at the run root marks a run whose agents carry a since-fixed defect. Such
a run is a valid record of the agent it actually was and is worthless pooled against a repaired run. The page
turns the file's own headline into an alert banner and a sticky top-bar badge, links the file, and tags the index
row — the file is the authority, the page is its messenger. A comparison page additionally names what pairing the
two sides *means*: a vintage contrast (one side spoiled — the deltas measure the repair, not any manipulation),
vintage-matched (both from the same spoiled run — like-for-like, the one safe reading), or two different spoiled
vintages (attributable to neither).

**Generation budget — informational, not a hazard.** A non-default budget is usually the arm's *intended*
budget: the frozen Opus cells run at a 16,384-token API floor on purpose. So it renders as a muted badge, and on
the index it is a lower-severity `hazardnote` excluded from the hazard count that drives sorting and the "has
hazards" filter — painting it the same red as a spoiled vintage would make every confirmatory episode look broken
and teach a reader to ignore the column. It stays in the filter's text haystack, and its tooltip says what it
costs: the row does not pair with a default-cap run, intended or not.

The frozen protocol caps a request at 2048 tokens (2560 on the forced final) and stamps
that on every request, while a *raised* cap is stamped only where it was raised — so the default is invisible by
design and the exception was invisible by accident. Two arms described as sharing a protocol ran at an 8x per-seat
budget difference. The badge therefore reads the caps the turns actually carry, and three sources rather than one:
the observed `cap` values, the `turn_max_tokens` protocol option from `cell_cfg`, and `api_request_config[…]
.turn_token_floor` from the manifest — that last one because an API participant applies its floor as
`max(cap, floor)`, so a cell whose every request says 2048 can have been generating at 16384. Muted-informational
rather than alarming: a raised cap is usually a deliberate choice, it is only never comparable.

## What counts as play: the census strip and silent turns

The contamination banner counts turns the *engine* fabricated, and is right to be loud about them. But it screens
for one cause, and a turn can carry nothing for others: a thinking model spending its whole budget inside an
unterminated `<think>` (generation succeeded, `gen_failed` is false), a move rejected as illegal and repeated on
its one retry, or a seat that talked and took no formal action. All three render as an ordinary quiet turn, and a
campaign cell reached **24% silent turns while passing every gate** because 0.000 fabricated was the honest
answer to the only question being asked.

So every episode page carries a **census strip** in its header — non-action rate, placeholder count, at-cap count,
each with its per-round breakdown on hover — present even when every count is zero, because "no turn of this
episode was silent" is a claim a reader needs and an absent strip cannot make it. A silent turn is marked as a
hazard on its card, in the scrubber, and in the conversation view, with a `SAID NOTHING` badge distinct from
`NOT GENERATED` (different cause, different fix), and the text the model *did* produce reachable in one click as
an unterminated-scratchpad panel. `raw` is carried for silent turns only — it runs to kilobytes and on a healthy
local turn merely repeats `content` — and capped at `RAW_EXCERPT_CHARS` (2048), because a turn that burned a
raised 32k budget inside one `<think>` block carries a hundred kilobytes and a page with a dozen of those is a
page nobody opens twice. The panel states the true length and says when it is showing less, so an excerpt cannot
pass for the whole generation; the untruncated text is in the episode record every page links to.

The at-cap heuristic is output within 2 tokens of the stamped cap — there is no `stop_reason` on the local
generation path — which is the same slack the campaign's own cell report uses, so a page and a report cannot
disagree about which turns were cut off.

## The final-vote tally

The forced final is the one turn where every seat answers the same question about the same package, so it is the
one place a missing answer is unambiguous. It is also where a defect hid for weeks: a computable seat voted on
whichever live offer it valued most rather than the one under the vote, the protocol rejected that as illegal, the
seat repeated itself on its retry, and the turn was recorded as a **pass** — which parses cleanly, so ~99% of one
arm's final ballots were silent abstentions that nothing on the page mentioned.

The tally is therefore built around absence: every seat asked to vote gets a row whether or not it produced a
ballot, and a missing ballot is called an abstention in the loudest style the page has.

**And "abstention" is where the page stops describing and starts quoting**, because the word undersells the
mechanism. The seat did not decline to vote — it voted, on the wrong offer id, and the record kept nothing. Both
halves of that signature are in the record, so the row prints both verbatim: the seat's own response
(`{"action": "accept", "offer_id": "P5"}`) and the protocol's rejection (`The final vote is only on P6; reference
that offer id.`). A ballot whose parse *succeeded* on a stale offer id is a third case and is distinguished from
both.

**The signature alone does not diagnose the defect; the seat's occupant does.** Measured across the Qwen3-8B
robustness subset: the same recording signature appears at 6 of 21 forced-final turns in `one_oracle` — all 6 at
computable-policy seats, which is the harness bug — and at 3 of 54 in `all_llm` and 3 of 44 in `one_rational`,
all of those at LLM seats, which is a model referencing a stale offer id under the same recording rule. Both are
real, they need different fixes, and only the occupant separates them; the row carries its occupant badge for
exactly this reason. An audit that counts silent final ballots across arms without splitting by occupant
attributes model errors to the harness and vice versa. Where a computable policy held the seat, its vote has an
offline answer; re-deriving it in the renderer would be a second opinion with no authority, so the derived column
reads gate G3's own output from `vote_derivation.json` (`gate_seeded_offer_votes.py --viz-sidecar`) and names a
recorded-vs-derived disagreement a harness bug in the row itself.

## Seat-swap comparison

Pairs episodes on `(instance_id, seed, arm, cell)` — a key, not a heuristic; an unmatched episode is reported, never approximately matched. The page opens with a **verdict strip** — which side won, on how many metrics, and the largest move in each direction, using each metric's own better-direction so a lower Gini counts as a win for whoever lowered it, and stating the ties rather than dropping them. Below it: a table of paired deltas (right minus left), one shared frontier carrying both trajectories, and two synchronized transcript columns with the first behavioural divergence marked. Each column renders with its own element-id prefix (`lturn-` / `rturn-`), because both sides number their turns from zero and a single prefix put duplicate ids on one page. The columns show each turn's action by default; a **Show each turn's post-hoc oracle counterfactual** toggle adds the per-turn oracle column and its value gap inside each side.

Turn slots are aligned on `(round, phase, seat)`, and after the divergence point the columns are deliberately presented as two independent trajectories rather than a line-by-line diff: from there on the two episodes are in different states, so the seats are answering different questions and a per-turn "diff" would be meaningless. Divergence is judged on *public* behaviour only (action, deal, offer, message) — two occupants that made the same move have not diverged just because one of them was a policy with no scratchpad to record.

Where several seats were swapped at once (a `mixed` table against `all_llm` replaces every seat but one), focal metrics are the **mean over the whole swapped set**, labelled with its size, because attributing the effect to any single one of those seats would be wrong.

`--select` decides which pairs a `--limit` keeps: `first` (arbitrary), `largest-effect`, or `deal-flip`. Ranking reads only stored outcomes, so it is free over hundreds of pairs. Prefer it to `first` for spot checks — a small `first` sample can easily be all no-deal-on-both and show nothing.

## Layout

| Module | Responsibility |
|---|---|
| `geometry.py` | the exact plottable geometry of one instance: frontier, solutions, party ideals, 2-D embedding |
| `episode.py` | episode + instance + annotation + manifest → one render payload; seat kinds; view provenance; the public offer ledger |
| `compare.py` | pairing, slot alignment, divergence, focal seats, the score table |
| `references.py` | the four decision references' 2x2, and the unit each one's `value` is priced in |
| `census.py` | the per-episode count of turns that carried nothing, and its header strip |
| `hazards.py` | the vintage hazard file, the generation budget, and their badges/banners |
| `ballots.py` | the final-vote tally and the optional re-derivation sidecar |
| `chrome.py` | the shell shared by all three page kinds: top bar, nav slot, help overlay, summary strip, and `slim_payload` (the pooled wire form) |
| `page.py` | pure `payload -> HTML`; renders every number server-side |
| `assets/` | the inline stylesheet and browser layer, split by job (see below) |
| `export.py` | the file-writing layer: pages, indexes, manifests, and the nav pass that links each page to its siblings |
| `serve.py` | `--serve`: a stdlib threading HTTP server over an output directory, plus the port-forward banner |
| `__main__.py` | the CLI |

Inside `assets/`: `css.py` (the design system — tokens, light/dark, the action grammar, layout), `js_core.py` (`JS_UTIL` formatting/DOM helpers plus `JS_CORE`, the payload and view rehydration), `js_chart.py` (frontier chart with hover/pin/zoom, regret strip), `js_transcript.py` (turn cards, scrubber, lazy prompt bodies, turn selection), `js_sidebar.py` (the tabbed sidebar and its scroll sync), `js_shell.py` (theme, navigation, keyboard, help), and one wiring module per page kind (`js_episode.py`, `js_compare.py`, `js_index.py`). The index loads only the helpers and the shell, since it carries no episode payload; the sidebar layer is in the shared bundle and is a no-op on a page with no `#sidebar`.

The split keeps `page.py` testable without a filesystem and `geometry.py`/`compare.py` testable without HTML. Because every number is rendered in Python and only the charts and transcript cards are drawn in the browser, [`tests/test_arena_viz.py`](../../../../../tests/test_arena_viz.py) asserts on real structure and real values with no browser involved (67 tests, including a `node --check` parse gate on all three page kinds' emitted scripts).

What genuinely only exists once the script runs — the scroll sync — is covered by [`tests/assets/viz_dom_harness.js`](../../../../../tests/assets/viz_dom_harness.js): it loads a rendered page into a DOM (`linkedom`), stubs the handful of browser APIs a DOM library lacks, executes the page's own script, and then *fires a synthetic `IntersectionObserver` event* so scrolling to a given turn is deterministic rather than approximated. It doubles as the no-runtime-errors check for every page kind. It needs node plus a `linkedom` install (`npm install linkedom` in `~/.cache/interlens-viz`, or point `INTERLENS_VIZ_NODE_MODULES` at one); without it those tests skip and the `node --check` gate remains the floor.
