# `references`

Module `interlens.arena.auction.references`

Citation-key registry for the auction mechanism, benchmark, and collusion-metric modules.

The sibling of `negotiation/references.py` and the same shape: every algorithm and every preregistered
benchmark in this package cites its primary source by a short key (e.g. `[vickrey1961]`) in the relevant
docstring, and this module maps each key to the full citation plus the **exact page range** the module relies
on. `design.md` §12 item 1 names the required entries; `prompt.md` requires the page numbers.

Usage — the registry is bibliography DATA (no accessor API); read it directly:

```python
from interlens.arena.auction.references import REFERENCES
REFERENCES["vickrey1961"].url          # -> 'https://www.jstor.org/stable/2977633'
str(REFERENCES["robinson1985"])        # "<citation> <url> — <note>" for a header line
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `REFERENCES` | dict[str, [Reference](../../negotiation/references/Reference.md)] |  |
