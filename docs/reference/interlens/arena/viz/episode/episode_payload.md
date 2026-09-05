# `episode_payload`

The complete render payload for one episode.

```python
episode_payload(
	episode: dict,
	instance: dict | None = None,
	annotation: dict | None = None,
	*,
	manifest: dict | None = None,
	geometry: GameGeometry | None = None,
	reconstruct: bool = True,
	paths: dict | None = None,
	annotations_source: str | None = None,
	vintage: dict | None = None,
	derivation: dict | None = None,
	advice: dict | None = None,
	auction_counterfactuals: bool = True,
) -> dict
```

Defined in [`interlens.arena.viz.episode`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/episode.py#L608-L770)

Parameters
----------
episode : dict
    A stored `Episode.to_json()` record.
instance : dict, optional
    The `Instance` record the episode was played on. Without it there is no game geometry, so the frontier
    and side panels are omitted and the page renders the transcript alone.
annotation : dict, optional
    The post-hoc annotation record (`{episode_id, summary, turns:[{turn_idx, oracle:{...}}]}`), which is
    where a re-scored oracle such as `bestresponse` lives for runs annotated after the fact.
manifest : dict, optional
    The run's `manifest.json`, read for the recorded invocation (seat kinds, policies, oracle list).
geometry : GameGeometry, optional
    A prebuilt geometry to reuse — pass the SAME object for both episodes of a comparison so the two
    trajectories are drawn against one identical frontier (and the `|D| x n` tables are built once).
reconstruct : bool
    When an episode carries no stored per-turn views, re-derive them by replay (see
    :func:`reconstruct_views`) and mark them `reconstructed`. `False` reports them as `absent`.
paths : dict, optional
    Absolute source paths to link from the page (`episode`, `instance`, `annotation`, `run`).
annotations_source : str, optional
    The name of the per-run annotation subdirectory the `annotation` record was read from (e.g.
    `"annotations"` or `"annotations_v1"`). Carried through to the page as provenance so an auditor can
    see WHICH annotation vintage the post-hoc oracle values (above all the `bestresponse` counterfactual)
    were read from — the v0 pass versus a re-annotated set such as the oracle seat-binding fix. `None` when
    the counterfactual oracles came only from the episode's own inline records, not an annotation store.
vintage : dict, optional
    The run's parsed `VINTAGE_PROVENANCE.md` hazard record (see
    :func:`~interlens.arena.viz.hazards.vintage_provenance`), which marks a run whose agents carry a known
    defect. Passed in rather than read here because it is a property of the run directory and one run's file
    serves all of its episodes. `None` means no hazard file, which is the healthy case.
derivation : dict, optional
    The run's optional `vote_derivation.json` sidecar (see
    :func:`~interlens.arena.viz.ballots.vote_derivation`), which lets the final-vote tally show what each
    computable seat's own policy re-derives beside what the record holds. `None` renders the recorded
    ballots alone.
advice : dict, optional
    The run's optional `advice_trace.json` sidecar (see
    :func:`~interlens.arena.viz.advice.advice_trace`), which carries, per advised turn, the evidence the
    seat's private planner ran on — the formal-move ledger counts and the chat-derived preference claims
    with their provenance quotes — its ranked recommendation, and the stored verdict on whether the seat
    played it. Attached to each advised turn as `advice`. `None` on any run with no advised seat, which
    is every arm but the advised ones; the transcript then renders exactly as before.
auction_counterfactuals : bool
    On an AUCTION episode, whether to compute the per-turn rational and oracle counterfactual bids (see
    :func:`~interlens.arena.viz.auction_geometry.auction_trace`). On by default because they are the
    campaign's headline instrumentation; `False` is the fast path when only the index row is wanted.
    Ignored for every other scenario.

Notes
-----
An AUCTION episode takes a different geometry: `GameGeometry` is `GameSpec`-shaped and returns `None`
on an auction payload, so `payload["game"]` stays `None` (which is what makes every negotiation panel
degrade away rather than render an empty frontier) and `payload["auction"]` carries the sibling geometry
plus the replay-derived per-episode trace. The two keys are mutually exclusive by construction.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `instance` | `dict \| None` | `None` |  |
| `annotation` | `dict \| None` | `None` |  |
| `manifest` | `dict \| None` | `None` |  |
| `geometry` | [GameGeometry](../geometry/GameGeometry.md) \| None | `None` |  |
| `reconstruct` | `bool` | `True` |  |
| `paths` | `dict \| None` | `None` |  |
| `annotations_source` | `str \| None` | `None` |  |
| `vintage` | `dict \| None` | `None` |  |
| `derivation` | `dict \| None` | `None` |  |
| `advice` | `dict \| None` | `None` |  |
| `auction_counterfactuals` | `bool` | `True` |  |
