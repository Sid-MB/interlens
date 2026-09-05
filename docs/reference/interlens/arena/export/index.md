# `interlens.arena.export`

Human-readable transcripts from stored episodes: an `EpisodeStore` tree -> one markdown + one self-contained
HTML page per episode, plus a per-run index.

Each transcript shows the game setup (issues/options, every seat's private sheet + threshold, the arm / protocol /
scaffold config), then every turn (seat, private scratchpad/reasoning, public cheap-talk message, the validated
action + offer id, and any per-oracle regret), then the outcome + welfare. It reads a stored `Episode` JSON
(`schema.Episode.to_json` shape) plus the `Instance` it was played on; it degrades gracefully on episodes
recorded before the per-turn `view` field existed (renders what is there) and surfaces the rendered `view`
when present.

Usage (library):

```python
from interlens.arena import export
md = export.render_markdown(episode_dict, instance_dict)
export.export_run("runs/episodes", "runs/instances", "runs/transcripts")   # -> writes md+html+index
```

CLI:

```python
python -m interlens.arena.export --episodes runs/episodes --instances runs/instances --out runs/transcripts
```

## Functions

| Name | Summary |
|---|---|
| [`export_episode`](export_episode.md) | Write `<id>.md` and `<id>.html` for one episode into `out_dir`; returns their paths. |
| [`export_run`](export_run.md) | Render every episode under `episodes_path` to `out_dir` (md + html each) plus an `index.html` / `index.md` linking them with one-line summaries. |
| [`export_transcripts`](export_transcripts.md) | Alias of :func:`export_run` with a caller-friendly signature (`episodes_dir, out_dir, instances_dir=`). |
| [`main`](main.md) |  |
| [`render_html`](render_html.md) | A self-contained (inline-CSS, no external assets) HTML transcript for one episode. |
| [`render_markdown`](render_markdown.md) | A full markdown transcript for one episode (setup header + per-turn + outcome/welfare). |
