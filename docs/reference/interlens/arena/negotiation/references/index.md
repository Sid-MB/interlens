# `references`

Module `interlens.arena.negotiation.references`

Citation-key registry for the negotiation solution-concept and generator modules.

Every algorithm in this package cites its primary source by a short key (e.g. `[nash1950]`) in the relevant
docstring; this module maps each key to the full citation (authors, year, title, venue, volume/pages, DOI) and
a stable URL, so the citations live in exactly one place and the docstrings stay terse. Keys and page/section
page and section references were verified against the fetched primary PDFs.

Usage — the registry is bibliography DATA (no accessor API); read it directly:

```python
from interlens.arena.negotiation.references import REFERENCES
REFERENCES["nash1950"].url         # -> 'https://www.jstor.org/stable/1907266'
str(REFERENCES["ks1975"])          # "<citation> <url> — <note>" for a header line
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `REFERENCES` | dict[str, [Reference](Reference.md)] |  |

## Classes

| Name | Summary |
|---|---|
| [`Reference`](Reference.md) | One bibliographic entry. |
