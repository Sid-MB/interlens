# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# [rational_agents: viz-upgrades] 2026-08-12

"""Two facts about a run that decide whether its numbers may be compared with another run's.

Both are properties of the RUN, not of the episode, and both were invisible on the pages for as long as they
existed — which is how each one cost this program weeks.

**Vintage.** A run whose agents carry a since-fixed defect is still a valid record of the agent it actually was,
and is worthless pooled against a repaired run. The convention is a ``VINTAGE_PROVENANCE.md`` at the run root
naming the defect and its repaired counterpart; :func:`vintage_provenance` reads it and the page turns it into
the loudest thing on the screen.

**Generation budget.** Two arms described as "sharing a protocol" ran at an 8x per-seat token budget difference,
because the frozen caps (2048 on an ordinary turn, 2560 on the forced final) are stamped on every request while
a RAISED cap is stamped only where it was raised. So the default is invisible by design and the exception was
invisible by accident. :func:`generation_budget` reads the caps the turns actually carry — the record, not the
intent — and reports any departure from the frozen pair.
"""
from __future__ import annotations

import re
from pathlib import Path

from .chrome import _e

#: The scorable negotiation's frozen per-request caps: an ordinary turn and the forced final. A run whose turns
#: carry only these ran the published protocol; anything else is a departure worth stating on the page. Kept
#: here rather than imported from the scenario because a rendered page must describe records written by any
#: version, including ones whose defaults have since moved.
FROZEN_TURN_CAPS = (2048, 2560)

#: How many lines of a ``VINTAGE_PROVENANCE.md`` the reader scans for its headline and summary. The convention
#: puts the headline in the first heading and the verdict in the paragraph under it; the rest is the audit trail,
#: which belongs behind the link rather than in a badge.
VINTAGE_SCAN_LINES = 40

#: The longest summary the banner will print. Past this the paragraph is the audit trail rather than the verdict,
#: and the file itself is one click away.
VINTAGE_SUMMARY_CHARS = 320


def _strip_comments(lines: list[str]) -> list[str]:
    """Drop HTML comment blocks, however many lines each spans, keeping any prose that shares a closing line.

    Line-wise skipping is not enough: a wrapped ``<!-- … -->`` header leaves its continuation lines behind, and
    the first one then reads as the file's headline. Tracks open/close across lines instead, and a comment that is
    never closed swallows the rest of the scan — which is the safe direction, since a malformed file still yields
    a record from its filename rather than quoting comment text at a reader."""
    out, inside = [], False
    for line in lines:
        kept, i = [], 0
        while i < len(line):
            if inside:
                end = line.find("-->", i)
                if end < 0:                       # the comment continues onto the next line
                    break
                i, inside = end + 3, False
                continue
            start = line.find("<!--", i)
            if start < 0:                         # no comment opens in the rest of this line
                kept.append(line[i:])
                break
            kept.append(line[i:start])            # prose before a comment on the same line survives
            i, inside = start + 4, True
        text = "".join(kept).strip()
        if text:
            out.append(text)
    return out


def _plain(markdown: str) -> str:
    """One line of markdown as plain text, for a banner that renders escaped rather than as HTML.

    Emphasis, code spans, and link syntax are stripped instead of being shown literally: the page escapes
    everything it prints (hostile model text must never become markup), so an unstripped ``**Arm:**`` reaches the
    reader as those exact characters. Only inline markers are touched — no structure is interpreted, because a
    hazard summary that silently reformatted its source would be the wrong kind of helpful."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", markdown)         # links keep their text
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def vintage_provenance(run_root: str | Path | None) -> dict | None:
    """The run's ``VINTAGE_PROVENANCE.md``, parsed into ``{path, headline, summary}``, or ``None`` if absent.

    ``headline`` is the file's first markdown heading, which by convention states the defect in one line
    (``# THIS ARM IS THE SPOILED-BALLOT VINTAGE — DO NOT POOL IT WITH A REPAIRED RUN``). ``summary`` is the first
    PARAGRAPH after it — consecutive lines up to the next blank, joined — rather than the first line, because a
    hard-wrapped source file would otherwise be quoted cut off mid-sentence. Comment lines are skipped, so a
    session-stamp comment at the top of the file does not become the headline, and inline markdown is reduced to
    plain text because the banner escapes everything it prints.

    A file that exists but has no heading still yields a record — with the headline falling back to the file's
    first non-comment line — because a malformed hazard file must not silently disarm the hazard.
    """
    if run_root is None:
        return None
    path = Path(run_root) / "VINTAGE_PROVENANCE.md"
    if not path.is_file():
        return None
    try:
        lines = [ln.strip() for ln in path.read_text().splitlines()[:VINTAGE_SCAN_LINES]]
    except OSError:
        return None
    # Comments are skipped as BLOCKS, not as lines. This repo's files open with a session stamp that routinely
    # wraps across two or three lines, and a line-wise filter takes the stamp's second line for the headline —
    # which is exactly what the first hazard file written to this convention did.
    lines = _strip_comments(lines)
    headline, paragraph, started = "", [], False
    for line in lines:
        if not headline:
            if line.startswith("#"):
                headline = _plain(line.lstrip("# "))
            elif line:
                headline = _plain(line)              # malformed file: its first real line still arms the hazard
            continue
        if line.startswith("#"):                      # a second heading ends the search for the verdict
            break
        if line:
            paragraph.append(_plain(line))
            started = True
        elif started:
            break
    summary = " ".join(p for p in paragraph if p)
    if len(summary) > VINTAGE_SUMMARY_CHARS:
        summary = summary[:VINTAGE_SUMMARY_CHARS].rsplit(" ", 1)[0] + "…"
    return {"path": str(path.resolve()), "headline": headline or path.name, "summary": summary}


def generation_budget(payload: dict) -> dict:
    """The per-seat generation budget this episode actually ran at, and whether it is the frozen default.

    Reads three sources, most authoritative first, and reports all three rather than collapsing them — a badge
    that said only "raised" would leave a reader unable to tell a protocol option from an API floor:

    - ``caps`` — the distinct ``max_tokens`` values stamped on this episode's own requests. This is the record.
    - ``turn_max_tokens`` — the protocol option that raised them, from the episode's ``cell_cfg``. Stamped only
      when set, which is exactly why it cannot be the detector.
    - ``api_floors`` — ``{model: turn_token_floor}`` from the run manifest's ``api_request_config``. An API
      participant applies its floor as ``max(cap, floor)``, so an API seat's effective budget is the floor even
      though the request's own cap says otherwise. This is the term that made two arms look matched when they
      were not.

    ``default`` is true only when the observed caps are a subset of :data:`FROZEN_TURN_CAPS` and no API floor
    exceeds them. ``effective`` is the largest budget any seat could actually use.
    """
    ep = payload.get("episode") or {}
    caps = sorted({int(t["cap"]) for t in payload.get("turns") or [] if t.get("cap")})
    turn_max = (ep.get("cell_cfg") or {}).get("turn_max_tokens")
    api = (payload.get("manifest") or {}).get("api_request_config") or {}
    floors = {name: int(cfg["turn_token_floor"]) for name, cfg in api.items()
              if isinstance(cfg, dict) and cfg.get("turn_token_floor")}
    ceiling = max(FROZEN_TURN_CAPS)
    raised_caps = [c for c in caps if c not in FROZEN_TURN_CAPS]
    raised_floors = {k: v for k, v in floors.items() if v > ceiling}
    effective = max([*caps, *floors.values()] or [None]) if (caps or floors) else None
    return {
        "caps": caps,
        "turn_max_tokens": turn_max,
        "api_floors": floors,
        "frozen": list(FROZEN_TURN_CAPS),
        "effective": effective,
        "default": not raised_caps and not raised_floors,
        "raised_caps": raised_caps,
        "raised_floors": raised_floors,
    }


# --------------------------------------------------------------------------------------- rendering --
def vintage_banner(vintage: dict | None) -> str:
    """The loudest banner on the page: this run carries a known defect and must not be pooled.

    Rendered above everything, links to the provenance file itself, and states its headline verbatim rather than
    a paraphrase — the file is the authority on what is wrong and the page is only its messenger."""
    if not vintage:
        return ""
    link = (f"<a href='{_e(Path(vintage['path']).as_uri())}'>VINTAGE_PROVENANCE.md</a>"
            if vintage.get("path") else "")
    summary = f"<span>{_e(vintage.get('summary'))}</span>" if vintage.get("summary") else ""
    return ("<div class='warn danger vintage' role='alert'>"
            f"<b>SPOILED VINTAGE — {_e(vintage.get('headline'))}</b>{summary}"
            f"<span class='sub'>This run directory carries a hazard file naming a defect in the agents that "
            f"played it. Its episodes are a valid record of those agents and MUST NOT be pooled with, or "
            f"contrasted against, a repaired run without labelling both vintages. Full statement: {link}</span>"
            "</div>")


def vintage_badge(vintage: dict | None) -> str:
    """The sticky quick-read marker for a spoiled vintage, so the hazard survives scrolling past the banner."""
    if not vintage:
        return ""
    return ("<span class='vintagequick' title='this run carries a VINTAGE_PROVENANCE.md hazard file'>"
            "<span class='k'>vintage</span> <b>SPOILED</b></span>")


def vintage_pairing(left: dict, right: dict, labels: dict) -> str:
    """What pairing THESE two episodes means, when either side carries a vintage hazard.

    The intended and most valuable use of a comparison page is a spoiled run against its repaired counterpart —
    the same instance and seed, one agent defect apart. But that is also the pairing whose deltas are easiest to
    misread: they are the effect of the REPAIR, not of any behavioural manipulation, so a page that showed them
    beside a seat-swap banner would invite exactly the wrong reading. Three cases, each stated in its own words:

    - **one side spoiled** — a vintage contrast; the deltas measure the fix.
    - **both spoiled by the same file** — vintage-matched, which is like-for-like and the one safe pooling of a
      spoiled arm.
    - **both spoiled by different files** — two different defects, so the deltas mix them and belong to neither.

    Silent when neither side carries a hazard, which is the ordinary case.
    """
    lv, rv = (left or {}).get("vintage"), (right or {}).get("vintage")
    if not lv and not rv:
        return ""
    if lv and rv and lv.get("path") == rv.get("path"):
        return ("<div class='warn'><b>Vintage-matched pair.</b> Both sides come from the same spoiled run, so "
                "the comparison is like-for-like: the defect is held fixed rather than being one of the things "
                "that differs. This is the one contrast a spoiled arm may be read in.</div>")
    if lv and rv:
        return ("<div class='warn danger'><b>Two different spoiled vintages.</b> Each side carries its own "
                "hazard file, so the deltas below mix two distinct agent defects and are attributable to "
                "neither. Repair both before reading them.</div>")
    spoiled = labels.get("left" if lv else "right")
    repaired = labels.get("right" if lv else "left")
    return ("<div class='warn danger'><b>Vintage contrast, not a behavioural comparison.</b> "
            f"<b>{_e(spoiled)}</b> carries a vintage hazard and <b>{_e(repaired)}</b> does not, so every delta "
            "below is the effect of REPAIRING the agent — closure, deal rate, and welfare included. It is not a "
            "measurement of any manipulation, and it must not be reported as one.</div>")


def budget_badge(budget: dict | None) -> str:
    """The per-seat generation budget, stated whenever it is not the frozen default.

    Muted-informational rather than alarming: a raised cap is a deliberate protocol choice and often the right
    one. What it is not is comparable — so the badge names the number and says which frozen pair it departs
    from, and stays silent on a default run so the exception reads as exceptional."""
    if not budget or budget.get("default"):
        return ""
    parts = []
    if budget.get("raised_caps"):
        parts.append("per-turn cap " + ", ".join(str(c) for c in budget["raised_caps"]))
    if budget.get("raised_floors"):
        parts.append("API floor " + ", ".join(f"{k}={v}" for k, v in sorted(budget["raised_floors"].items())))
    frozen = "/".join(str(c) for c in budget.get("frozen") or FROZEN_TURN_CAPS)
    return (f"<span class='budgetbadge' title='the frozen protocol generates at {_e(frozen)} tokens per turn; "
            f"this episode did not, so its turn lengths do not pair with a default-cap run'>"
            f"<span class='k'>token budget</span> <b>{_e(' · '.join(parts))}</b>"
            f"<span class='muted'>vs frozen {_e(frozen)}</span></span>")


def budget_note(budget: dict | None) -> str:
    """A one-line explanation under the header for a non-default generation budget, naming what it blocks."""
    if not budget or budget.get("default"):
        return ""
    return ("<div class='warn budgetnote'><b>This episode did not run at the frozen generation budget.</b> "
            f"Requests carried caps {_e(', '.join(str(c) for c in budget.get('caps') or []) or 'none recorded')}"
            + (f"; the protocol option <code>turn_max_tokens</code> was set to "
               f"{_e(budget.get('turn_max_tokens'))}" if budget.get("turn_max_tokens") else "")
            + (f"; API seats applied a per-turn floor of "
               f"{_e(', '.join(f'{k}={v}' for k, v in sorted((budget.get('api_floors') or {}).items())))}"
               if budget.get("api_floors") else "")
            + f". The frozen protocol is {_e('/'.join(str(c) for c in budget.get('frozen') or []))} "
              "(ordinary turn / forced final). Turn lengths, at-cap rates, and anything downstream of how much "
              "the seats could say do not pair with a default-cap run.</div>")
