<!-- [rational_agents: viz] 2026-07-29 -->

# `interlens.arena.viz` — interactive episode visualizer

The project's shared renderer for negotiation episodes. Point it at any run directory; get one self-contained interactive HTML page per episode, plus a run index. Where [`arena/export.py`](../export.py) answers *what was said*, this answers *was it any good*: every deal placed against the exact Pareto frontier and the axiomatic solution points, every turn's action beside what a rational agent would have done there with the regret between them, and every prompt the models actually saw, expandable and marked with its provenance.

Pages are opened over `file://` — no server, no build step, no network assets of any kind. Light and dark are both explicitly styled and the viewer's theme toggle wins over the OS setting.

## Quick start

```bash
# one page per episode of a run, plus index.html and manifest.json
python -m interlens.arena.viz --run /nlp/scr/$USER/ii_mats/rational_agents/p2_pilot_qwen3_4b_v2 \
                              --out .claude/products/episode_viz/pilot --limit 3

# seat-swap comparison: same instance + seed, one seat's occupant swapped
python -m interlens.arena.viz --compare RUN_all_llm RUN_mixed \
                              --out .claude/products/episode_viz/seatswap --limit 4 --select deal-flip
```

Every flag is documented in `--help`. From Python:

```python
from interlens.arena import viz

viz.export_run(run_dir, out_dir, limit=3)                    # pages + index, returns a manifest
viz.export_comparison(left_run, right_run, out_dir, select="largest-effect")
html = viz.render_episode(run_dir, episode_json_path)        # the HTML as a string, nothing written
payload = viz.RunDir(run_dir).payload(episode_json_path)     # every number the page shows, as a dict
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

Up and to the right is better for everyone, so the frontier's image is the upper-right envelope. Marked on it: the play trajectory as numbered points, the deal that closed, the oracle's recommendation at each turn, the five solution concepts (NBS, KS, utilitarian, egalitarian, MNW), and each party's individually-best efficient deal. Hovering any deal — all `|D|` of them, not just the marked ones — opens its full per-party breakdown: utility, threshold, surplus, and share of that party's ideal.

The projection is lossy on purpose, and the code never uses it to decide anything: whether a deal is Pareto-optimal always comes from the exact `pareto_mask`, never from its position on the chart. A deal can therefore sit strictly inside the drawn envelope while being genuinely efficient.

## Colour

Categorical identity is capped at **three** slots, which is the binding all-pairs constraint of the colour formula for a scatter (validated in both modes with `dataviz/scripts/validate_palette.js --pairs all`). Slot 1 is what the model did (or the left episode), slot 2 the oracle's recommendation (or the right episode), slot 3 the normative solution points. Everything else is **shape plus a direct label**: solution concepts share one colour and are each labelled on the chart, per-party ideals share one diamond, and deals themselves are chart chrome rather than a series. Slot 3 falls below 3:1 on the light surface, so the relief rule applies — hence the always-visible labels and the numeric table view that ships with every chart.

## Prompt provenance

Auditing what a model saw only means something if the page is honest about where the text came from. Three states, each labelled in place:

- **stored** — the exact view recorded at generation time (`TurnRecord.view`).
- **reconstructed** — re-derived by deterministic replay through the scenario state machine, because the episode predates view capture. Byte-exact for the state, but rendered by *today's* prompt code.
- **reconstructed_pre_retry** — as above, on a turn that was a retry after a malformed response. Replay re-issues the original request, so this is the **first attempt's** prompt; the repair instruction the model actually saw on the retry is not recoverable from the record. Marked separately so a prompt audit can see which panels are known-incomplete.

`--no-reconstruct-views` disables reconstruction entirely, which is what you want when the pages must contain only bytes that were genuinely recorded.

## Seat-swap comparison

Pairs episodes on `(instance_id, seed, arm, cell)` — a key, not a heuristic; an unmatched episode is reported, never approximately matched. The page shows a table of paired deltas (right minus left), one shared frontier carrying both trajectories, and two synchronized transcript columns with the first behavioural divergence marked.

Turn slots are aligned on `(round, phase, seat)`, and after the divergence point the columns are deliberately presented as two independent trajectories rather than a line-by-line diff: from there on the two episodes are in different states, so the seats are answering different questions and a per-turn "diff" would be meaningless. Divergence is judged on *public* behaviour only (action, deal, offer, message) — two occupants that made the same move have not diverged just because one of them was a policy with no scratchpad to record.

Where several seats were swapped at once (a `mixed` table against `all_llm` replaces every seat but one), focal metrics are the **mean over the whole swapped set**, labelled with its size, because attributing the effect to any single one of those seats would be wrong.

`--select` decides which pairs a `--limit` keeps: `first` (arbitrary), `largest-effect`, or `deal-flip`. Ranking reads only stored outcomes, so it is free over hundreds of pairs. Prefer it to `first` for spot checks — a small `first` sample can easily be all no-deal-on-both and show nothing.

## Layout

| Module | Responsibility |
|---|---|
| `geometry.py` | the exact plottable geometry of one instance: frontier, solutions, party ideals, 2-D embedding |
| `episode.py` | episode + instance + annotation + manifest → one render payload; seat kinds; view provenance |
| `compare.py` | pairing, slot alignment, divergence, focal seats, the score table |
| `page.py` | pure `payload -> HTML`; renders every number server-side |
| `assets.py` | the inline stylesheet and the browser layer (charts + transcript cards only) |
| `export.py` | the file-writing layer: pages, indexes, manifests |
| `__main__.py` | the CLI |

The split keeps `page.py` testable without a filesystem and `geometry.py`/`compare.py` testable without HTML. Because every number is rendered in Python and only the charts and transcript cards are drawn in the browser, [`tests/test_arena_viz.py`](../../../../../tests/test_arena_viz.py) asserts on real structure and real values with no browser involved.
