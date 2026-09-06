# `build`

Module `interlens.arena.scenarios.dlc.build`

Instance builders for the distributed long-context tasks — fetch, shard, and save instance banks.

Benchmark data does **not** ship in this repo: each builder fetches from the benchmark's own source at a
pinned revision (override `revision=` to move the pin) and writes a `load_instances`-compatible JSON bank.
Requires the `benchmarks` extra (`pip install interlens[benchmarks]`) for the HuggingFace `datasets`
dependency; the import is lazy so the rest of the arena never needs it.

Every builder partitions the assembled context into 4 contiguous shards and **asserts the partition
property**: the concatenation of the shards reproduces the original context exactly (no overlap, no loss).
The split helpers (`char_split4`, `char_balanced_split`, `char_split4_docs`) are module-level so the
property is unit-testable without network.

Builders (sources pinned to the revisions used when the instance banks were produced):

- `build_sniah` — RULER-style single needle-in-a-haystack over Paul Graham essays
  (`sgoel9/paul_graham_essays`).
- `build_oolong` — OOLONG-Pairs pairwise aggregation over `oolongbench/oolong-synth` trec_coarse windows;
  gold pair sets computed from the dataset's own labels.
- `build_codeqa` — LongBench-v2 'Code Repository Understanding' multiple choice (`THUDM/LongBench-v2`).
- `build_bcp` — BrowseComp-Plus multi-hop QA (`Tevatron/browsecomp-plus` + `-corpus`); queries/answers
  decrypted with the dataset's published canary.

Note: the source experiment's banks were built before this pinning convention, so the pins record the
datasets' revisions at export time; the experiment's saved banks (not a re-fetch) remain the source of truth
for reproducing its episodes exactly.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `CANARY` |  |  |
| `CHARS_PER_TOKEN` |  |  |
| `REVISIONS` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`build_bcp`](build_bcp.md) | BrowseComp-Plus instances: decrypt queries with the published canary, then assemble a per-instance corpus of gold + evidence docs (guaranteed present) + seeded filler negatives up to `k_docs`. |
| [`build_codeqa`](build_codeqa.md) | LongBench-v2 'Code Repository Understanding' instances, seeded-sampled stratified by difficulty. |
| [`build_haystack`](build_haystack.md) |  |
| [`build_oolong`](build_oolong.md) | OOLONG-Pairs instances: the 20 paper queries x the trec_coarse windows at `context_len`. |
| [`build_sniah`](build_sniah.md) | Seeded PG-essay haystacks + one needle each; the needle is inserted BEFORE the 4-way split, so exactly one shard unknowingly holds it (holder index and depth recorded in the payload metadata). |
| [`char_balanced_split`](char_balanced_split.md) | Contiguous split of whole lines into `k` blocks with roughly equal characters. |
| [`char_split4`](char_split4.md) | 4 contiguous shards cut at line boundaries near the character quartiles; concatenation == text. |
| [`char_split4_docs`](char_split4_docs.md) | 4 contiguous shards over whole documents, balanced by characters; concatenation == "".join(docs). |
| [`data_lines`](data_lines.md) |  |
| [`dec_obj`](dec_obj.md) |  |
| [`decrypt`](decrypt.md) | Decrypt one BrowseComp-Plus field with the dataset's published canary. |
| [`fetch_oolong_windows`](fetch_oolong_windows.md) | `window_id -> {'plain': str, 'labeled': str}` for trec_coarse windows at `context_len`. |
| [`fmt_doc`](fmt_doc.md) |  |
| [`insert_needle`](insert_needle.md) | Paragraph-boundary insertion at a seeded uniform depth. |
