# `export`

Module `interlens.arena.viz.export`

The file-writing layer: run directory in, HTML pages plus an index on disk out.

Kept apart from :mod:`~interlens.arena.viz.page` (which is pure `payload -> string`) so every renderer stays
testable without touching a filesystem, and so a caller that wants the HTML in memory — to embed it, serve it, or
diff it — never has to write a file to get it.

## Functions

| Name | Summary |
|---|---|
| [`export_comparison`](export_comparison.md) | Pair two runs on `pair_fields` and write one comparison page per matched pair, plus an index and the pairing report. |
| [`export_episode`](export_episode.md) | Write one episode's page into `out_dir` as `<episode_id>.html` and return its path. |
| [`export_run`](export_run.md) | Render every episode of a run to its own page in `out_dir`, plus an `index.html` listing them with the numbers that say which are worth opening. |
| [`render_compare`](render_compare.md) | The interactive HTML for the `index`-th matched pair between two runs, as a string. |
| [`render_episode`](render_episode.md) | The interactive HTML for one episode of a run, as a string. |
