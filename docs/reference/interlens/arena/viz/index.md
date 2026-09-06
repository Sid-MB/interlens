# `viz`

Package `interlens.arena.viz`

Interactive episode visualization: any arena run directory in, self-contained interactive HTML out.

This is the shared renderer for negotiation episodes — the graphical counterpart of
:mod:`interlens.arena.export`, which produces the flat markdown/HTML transcript. Where the exporter answers "what
was said", this answers "was it any good": every deal placed against the exact Pareto frontier and the axiomatic
solution points, every turn's action next to the post-hoc oracle counterfactual and its value gap
them, and every prompt the models actually saw, expandable and marked with its provenance.

Swapping a run in is one call — nothing about a run is hard-coded, and the same renderer serves any scenario whose
instances carry a scorable game (episodes without one still render their transcript, minus the game panels).

Two modes:

**Per episode** — one page each, plus a run index:

```python
from interlens.arena import viz
viz.export_run("runs/p2_pilot", "products/viz")                 # every episode + index.html
viz.export_run("runs/p2_pilot", "products/viz", limit=3)        # just the first three

html = viz.render_episode("runs/p2_pilot", "runs/p2_pilot/episodes/.../abc.json")
```

**Seat-swap comparison** — the same instance and seed played with a different occupant in one seat:

```python
viz.export_comparison("runs/p2_X_all_llm", "runs/p2_X_mixed", "products/viz_compare", limit=4)
```

CLI (self-documenting, `--help` on every argument):

```python
python -m interlens.arena.viz --run RUN_DIR --out OUT_DIR [--limit N]
python -m interlens.arena.viz --compare LEFT_RUN RIGHT_RUN --out OUT_DIR [--pair-key instance_id seed arm]
```

The pages are self-contained: inline CSS and JS, no network requests, no build step, light and dark aware. They
open by double-click from a filesystem path.

**Looking at them from a cluster node** — when the run is on a machine with no browser, drop `--out` (the
pages go to a temporary directory) and add `--serve` (a stdlib HTTP server on a free port, which prints the URL
and the `ssh -L` command to forward it):

```python
python -m interlens.arena.viz --run runs/p2_pilot --limit 5 --serve
python -m interlens.arena.viz --run runs/p2_pilot --serve --port 8899   # a standing tunnel's port
```

See :func:`~interlens.arena.viz.serve.serve_directory` to do the same from Python.

## Modules

- [`advice`](advice/index.md) — The advised seat, audited: what its planner knew, what it recommended, and whether the seat did it.
- [`assets`](assets/index.md) — The inline stylesheet and browser layer — no external assets of any kind.
- [`auction_geometry`](auction_geometry/index.md) — The plottable geometry of one repeated-auction episode — the `AuctionSpec`-shaped sibling of :class:`~interlens.arena.viz.geometry.GameGeometry`.
- [`auction_page`](auction_page/index.md) — The auction episode page's own panels — the four charts design.md §10 commits to, plus the per-turn counterfactual table.
- [`ballots`](ballots/index.md) — The final vote, as a tally a reader can check at a glance — including the ballots that were never recorded.
- [`census`](census/index.md) — How much of an episode is actually play: the per-turn census, and the strip that puts it in the page header.
- [`chrome`](chrome/index.md) — The shell every page wears, and the wire form of the payload it carries.
- [`compare`](compare/index.md) — Seat-swap comparison: the same game instance played twice, with one seat's occupant swapped.
- [`concepts`](concepts/index.md) — What each solution concept IS, in one place, for every part of the visualizer that explains one to a reader.
- [`episode`](episode/index.md) — One stored episode, turned into the single JSON payload the interactive page renders.
- [`export`](export/index.md) — The file-writing layer: run directory in, HTML pages plus an index on disk out.
- [`geometry`](geometry/index.md) — The plottable geometry of one negotiation instance: every deal placed in a 2-D scale-invariant embedding, with the frontier, the axiomatic solution points, and each party's individually-best deal marked.
- [`hazards`](hazards/index.md) — Two facts about a run that decide whether its numbers may be compared with another run's.
- [`page`](page/index.md) — HTML assembly: a payload in, one self-contained interactive page out.
- [`references`](references/index.md) — The decision references a scored turn can carry, placed on two axes — and what each one's number MEANS.
- [`serve`](serve/index.md) — Hand the rendered pages to a browser over HTTP, for when the filesystem the pages live on is not the one the browser runs on.

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`ADVICE_SIDECAR`](advice/index.md#attributes) | `interlens.arena.viz.advice` |  |
| [`DEFAULT_HOST`](serve/index.md#attributes) | `interlens.arena.viz.serve` |  |
| [`DEFAULT_PAIR_KEY`](compare/index.md#attributes) | `interlens.arena.viz.compare` |  |
| [`DERIVATION_SIDECAR`](ballots/index.md#attributes) | `interlens.arena.viz.ballots` |  |
| [`DealGeometry`](geometry/DealGeometry.md) | `interlens.arena.viz.geometry` | One deal's full record: where it plots, and how every party feels about it. |
| [`FROZEN_TURN_CAPS`](hazards/index.md#attributes) | `interlens.arena.viz.hazards` |  |
| [`GameGeometry`](geometry/GameGeometry.md) | `interlens.arena.viz.geometry` | The exact, fully-enumerated geometry of one negotiation instance, ready to plot. |
| [`NAV_MARKER`](chrome/index.md#attributes) | `interlens.arena.viz.chrome` |  |
| [`RAW_EXCERPT_CHARS`](episode/index.md#attributes) | `interlens.arena.viz.episode` |  |
| [`RETRY_SOURCE`](episode/index.md#attributes) | `interlens.arena.viz.episode` |  |
| [`RunDir`](episode/RunDir.md) | `interlens.arena.viz.episode` | A run directory's three record stores, indexed for lookup: `episodes/`, `instances/`, and the annotation subdirectory named by `annotations_dirname` (`annotations/` by default), plus `manifest.json`. |
| [`SELECTIONS`](compare/index.md#attributes) | `interlens.arena.viz.compare` |  |
| [`SIDEBAR_TABS`](page/index.md#attributes) | `interlens.arena.viz.page` |  |
| [`advice_card`](advice/advice_card.md) | `interlens.arena.viz.advice` | The episode's advice audit as one server-rendered section, or `""` when no turn was advised. |
| [`advice_summary`](advice/advice_summary.md) | `interlens.arena.viz.advice` | This episode's compliance record: how many turns were advised, how many followed, on which rung. |
| [`advice_trace`](advice/advice_trace.md) | `interlens.arena.viz.advice` | The optional advice sidecar for a run, or `None` when it is absent or unreadable. |
| [`align`](compare/align.md) | `interlens.arena.viz.compare` | Align two episode payloads slot by slot and locate the divergence point. |
| [`attach_advice`](advice/attach_advice.md) | `interlens.arena.viz.advice` | Turn payload rows with each advised turn's trace row attached under `advice`. |
| [`ballot_table`](ballots/ballot_table.md) | `interlens.arena.viz.ballots` | The final-vote tally as a card, or nothing when the episode has no final-vote phase. |
| [`census_strip`](census/census_strip.md) | `interlens.arena.viz.census` | The per-episode census as a compact header strip, always rendered when there are turns to count. |
| [`compare_payload`](compare/compare_payload.md) | `interlens.arena.viz.compare` | One seat-swap comparison, ready to render: both episode payloads, the slot alignment, the divergence point, the focal seat(s), and the score table. |
| [`distance_to_nbs`](chrome/distance_to_nbs.md) | `interlens.arena.viz.chrome` | How far the deal that closed sits from the Nash bargaining solution, in the chart's own plane. |
| [`episode_advice`](advice/episode_advice.md) | `interlens.arena.viz.advice` | One episode's advised turns from the trace, keyed by turn index as a string. |
| [`episode_payload`](episode/episode_payload.md) | `interlens.arena.viz.episode` | The complete render payload for one episode. |
| [`export_comparison`](export/export_comparison.md) | `interlens.arena.viz.export` | Pair two runs on `pair_fields` and write one comparison page per matched pair, plus an index and the pairing report. |
| [`export_episode`](export/export_episode.md) | `interlens.arena.viz.export` | Write one episode's page into `out_dir` as `<episode_id>.html` and return its path. |
| [`export_run`](export/export_run.md) | `interlens.arena.viz.export` | Render every episode of a run to its own page in `out_dir`, plus an `index.html` listing them with the numbers that say which are worth opening. |
| [`final_ballots`](ballots/final_ballots.md) | `interlens.arena.viz.ballots` | The episode's final vote as `{offer, rows, n_ballots, n_abstentions, n_retries, n_mismatch, derived}`. |
| [`focal_seats`](compare/focal_seats.md) | `interlens.arena.viz.compare` | The seats whose OCCUPANT KIND differs between the two episodes — the substitution being measured. |
| [`generation_budget`](hazards/generation_budget.md) | `interlens.arena.viz.hazards` | The per-seat generation budget this episode actually ran at, and whether it is the frozen default. |
| [`inject_nav`](chrome/inject_nav.md) | `interlens.arena.viz.chrome` | Put a page's navigation into its top bar. |
| [`make_server`](serve/make_server.md) | `interlens.arena.viz.serve` | Bind (but do not run) an HTTP server rooted at `directory`. |
| [`nav_group`](chrome/nav_group.md) | `interlens.arena.viz.chrome` | The prev/next links and episode picker for the page at `position` in `rows`. |
| [`pair_key`](compare/pair_key.md) | `interlens.arena.viz.compare` | The pairing key of an episode: the tuple of its `fields`. |
| [`pair_runs`](compare/pair_runs.md) | `interlens.arena.viz.compare` | Pair every episode of one run against its key-matched counterpart in another, and build a comparison payload for each. |
| [`public_ledger`](episode/public_ledger.md) | `interlens.arena.viz.episode` | Reconstruct what the seats publicly saw, from the per-turn records alone. |
| [`reconstruct_views`](episode/reconstruct_views.md) | `interlens.arena.viz.episode` | Re-derive each turn's rendered view by deterministic replay, for episodes recorded before the per-turn `view` field existed. |
| [`render_compare`](export/render_compare.md) | `interlens.arena.viz.export` | The interactive HTML for the `index`-th matched pair between two runs, as a string. |
| [`render_compare_html`](page/render_compare_html.md) | `interlens.arena.viz.page` | One self-contained page for a seat-swap comparison: a verdict strip, the quantified score table with paired deltas, one shared frontier carrying both trajectories, and two synchronized transcript columns with the divergence point marked. |
| [`render_episode`](export/render_episode.md) | `interlens.arena.viz.export` | The interactive HTML for one episode of a run, as a string. |
| [`render_episode_html`](page/render_episode_html.md) | `interlens.arena.viz.page` | One self-contained interactive page for one episode. |
| [`render_index_html`](page/render_index_html.md) | `interlens.arena.viz.page` | A run index: one row per generated page, sortable on every column and filterable by text, outcome, and whether the engine fabricated any turns. |
| [`round_ledger`](advice/round_ledger.md) | `interlens.arena.viz.advice` | Per round, every advised seat's turn side by side — the shape an all-advised arm is read in. |
| [`round_ledger_card`](advice/round_ledger_card.md) | `interlens.arena.viz.advice` | The per-round, all-seats view, or `""` on an episode that advises fewer than two seats. |
| [`score_table`](compare/score_table.md) | `interlens.arena.viz.compare` | The quantified comparison: one row per metric with both values and the paired delta `right - left`. |
| [`seat_kinds`](episode/seat_kinds.md) | `interlens.arena.viz.episode` | Which seats an LLM played and which a computable policy played. |
| [`serve_banner`](serve/serve_banner.md) | `interlens.arena.viz.serve` | The startup message: where the pages are, the URL to open, and — because the reader is usually on a cluster node with no browser — the exact `ssh -L` command to forward `port` to their laptop, with this machine's real hostname already filled in. |
| [`serve_directory`](serve/serve_directory.md) | `interlens.arena.viz.serve` | Serve `directory` over HTTP until interrupted — bind, print :func:`serve_banner`, then block in `serve_forever`. |
| [`slim_payload`](chrome/slim_payload.md) | `interlens.arena.viz.chrome` | A copy of `payload` whose per-turn prompt views are indices into a shared `msgpool`. |
| [`staircase`](geometry/staircase.md) | `interlens.arena.viz.geometry` | The left-to-right monotone staircase of the masked points in the 2-D embedding: those not dominated on `(wx, wy)` by another masked point. |
| [`summary_strip`](chrome/summary_strip.md) | `interlens.arena.viz.chrome` | The whole episode in one row: did it close, how good was it, how far from the normative anchor, who was left below their threshold, how much of it the engine fabricated, how long it ran, what it cost. |
| [`turn_census`](census/turn_census.md) | `interlens.arena.viz.census` | Count the ways this episode's turns carried nothing, from the payload's own turn rows. |
| [`unslim_payload`](chrome/unslim_payload.md) | `interlens.arena.viz.chrome` | The inverse of :func:`slim_payload`: pooled view indices back to full `{role, content}` messages. |
| [`vintage_provenance`](hazards/vintage_provenance.md) | `interlens.arena.viz.hazards` | The run's `VINTAGE_PROVENANCE.md`, parsed into `{path, headline, summary}`, or `None` if absent. |
| [`vote_derivation`](ballots/vote_derivation.md) | `interlens.arena.viz.ballots` | The optional per-turn re-derivation sidecar for a run, or `None` when it is absent or unreadable. |
