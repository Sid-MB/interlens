# `sniah`

Module `interlens.arena.scenarios.dlc.sniah`

S-NIAH: RULER-style single needle-in-a-haystack (paper §3.1).

Haystack: seeded concatenation of Paul Graham essays (RULER's corpus).
Needle: "One of the special magic numbers for {word} is: {number}." inserted
at a seeded depth. Question asks for the number; grading is exact match on
the 7-digit number (RULER protocol).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `NEEDLE_TMPL` |  |  |
| `WORDS` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`SniahAdapter`](SniahAdapter.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`question_text`](question_text.md) |  |
