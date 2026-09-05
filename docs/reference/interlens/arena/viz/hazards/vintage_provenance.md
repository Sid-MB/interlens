# `vintage_provenance`

The run's `VINTAGE_PROVENANCE.md`, parsed into `{path, headline, summary}`, or `None` if absent.

```python
vintage_provenance(run_root: str | Path | None) -> dict | None
```

Defined in [`interlens.arena.viz.hazards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/hazards.py#L99-L143)

`headline` is the file's first markdown heading, which by convention states the defect in one line
(`# THIS ARM IS THE SPOILED-BALLOT VINTAGE — DO NOT POOL IT WITH A REPAIRED RUN`). `summary` is the first
PARAGRAPH after it — consecutive lines up to the next blank, joined — rather than the first line, because a
hard-wrapped source file would otherwise be quoted cut off mid-sentence. Comment lines are skipped, so a
session-stamp comment at the top of the file does not become the headline, and inline markdown is reduced to
plain text because the banner escapes everything it prints.

A file that exists but has no heading still yields a record — with the headline falling back to the file's
first non-comment line — because a malformed hazard file must not silently disarm the hazard.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `run_root` | `str \| Path \| None` | *required* |  |
