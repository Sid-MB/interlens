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
# [rational_agents: viz] 2026-07-29
# [rational_agents: viz-ux] 2026-08-03

"""The one stylesheet every page wears — a small design system, inlined.

Three things make this a system rather than a pile of rules:

**Tokens, in one place.** Colour, spacing (``--sp-*``), type scale (``--t-*``) and radii are custom properties
declared once. Light is the default declaration; dark is *selected* — the same roles re-stated for the dark
surface under BOTH the OS media query and an explicit ``data-theme`` scope, so the page's own theme toggle wins in
either direction rather than only being able to follow the OS.

**Categorical colour is capped at three** (``--s1``/``--s2``/``--s3``), the binding all-pairs constraint for a
scatter; everything else is shape, position, or the reserved status palette. Action types on the transcript wear
status colours (accept = good, reject = serious, walk = critical) because they are *states*, never a series — and
each one ships with a glyph and a word, so colour never carries the meaning alone.

**Nothing is decorative.** Borders are hairlines, grid and axis ink is recessive, and the only heavy weights on the
page are the numbers a reader came for.
"""
from __future__ import annotations

# --- tokens ------------------------------------------------------------------------------------------------
# Declared once for light, re-stated verbatim for dark under the OS query and the explicit theme stamp. The
# `:where()` on the media block keeps its specificity at zero so a `data-theme="light"` stamp beats OS-dark.
_DARK = """
 color-scheme:dark;
 --surface-1:#1a1a19; --surface-2:#222220; --plane:#0d0d0d; --ink:#fff; --ink-2:#c3c2b7; --muted:#898781;
 --grid:#2c2c2a; --axis:#383835; --ring:rgba(255,255,255,.10); --ring-2:rgba(255,255,255,.18);
 --s1:#3987e5; --s2:#d95926; --s3:#199e70; --up:#0ca30c; --shadow:0 1px 2px rgba(0,0,0,.5);
"""

CSS = """
:root{
 color-scheme:light;
 --surface-1:#fcfcfb; --surface-2:#f3f2ef; --plane:#f9f9f7; --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
 --grid:#e1e0d9; --axis:#c3c2b7; --ring:rgba(11,11,11,.10); --ring-2:rgba(11,11,11,.18);
 --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a;
 --good:#0ca30c; --warn:#fab219; --serious:#ec835a; --critical:#d03b3b; --up:#006300;
 --shadow:0 1px 2px rgba(11,11,11,.06);
 --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:24px; --sp-6:32px;
 --t-xs:.72rem; --t-sm:.8rem; --t-md:.87rem; --t-lg:1rem; --t-xl:1.25rem;
 --r-1:6px; --r-2:9px; --r-3:12px;
 /* the sticky stack, tallest-first: each layer parks directly under the one above it, so a turn header never
    slides beneath the scrubber and the scrubber never slides beneath a comparison column header */
 --topbar:46px; --scrubh:34px; --colhdh:36px;
}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){""" + _DARK + """}}
:root[data-theme="dark"]{""" + _DARK + """}

*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:calc(var(--topbar) + var(--scrubh) + var(--sp-3))}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--plane);color:var(--ink);
 font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-text-size-adjust:100%}
main{max-width:1560px;margin:0 auto;padding:var(--sp-4) var(--sp-4) var(--sp-6)}
h1{font-size:var(--t-xl);margin:0 0 var(--sp-1);font-weight:600;letter-spacing:-.01em}
h2{font-size:var(--t-lg);margin:0 0 var(--sp-2);font-weight:600;letter-spacing:-.005em}
h3{font-size:var(--t-md);margin:var(--sp-4) 0 var(--sp-1);color:var(--ink-2);font-weight:600}
a{color:var(--s1);text-underline-offset:2px}
code,kbd{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85em}
kbd{border:1px solid var(--ring-2);border-radius:4px;padding:1px 5px;background:var(--surface-2);
 color:var(--ink);font-size:.78em;white-space:nowrap}
.sub{color:var(--ink-2);font-size:var(--t-md)}
.muted{color:var(--muted)}
.neg{color:var(--critical)} .pos{color:var(--up)} .zero{color:var(--muted)}
.card{background:var(--surface-1);border:1px solid var(--ring);border-radius:var(--r-3);
 padding:var(--sp-4);margin-bottom:var(--sp-3)}

/* --- top bar: run identity, episode navigation, the quick read, the controls ------------------------------ */
.topbar{position:sticky;top:0;z-index:40;display:flex;align-items:center;gap:var(--sp-3);flex-wrap:wrap;
 height:auto;min-height:var(--topbar);padding:var(--sp-1) var(--sp-4);background:var(--surface-1);
 border-bottom:1px solid var(--ring);box-shadow:var(--shadow)}
.topbar .brand{font-weight:600;font-size:var(--t-md);color:var(--ink);text-decoration:none;white-space:nowrap;
 max-width:30ch;overflow:hidden;text-overflow:ellipsis}
.topbar .brand:hover{color:var(--s1)}
.topbar .spacer{flex:1 1 auto}
.navgrp{display:flex;align-items:center;gap:var(--sp-1)}
.navgrp select{max-width:38ch}
.navgrp .pos{color:var(--muted);font-size:var(--t-xs);font-variant-numeric:tabular-nums;white-space:nowrap}
.quick{display:flex;gap:var(--sp-3);align-items:baseline;flex-wrap:wrap;font-size:var(--t-sm);color:var(--ink-2);
 font-variant-numeric:tabular-nums}
.quick b{color:var(--ink);font-weight:600}
.quick .k{color:var(--muted);font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.04em}
a.disabled,button:disabled{opacity:.38;pointer-events:none}

/* --- controls -------------------------------------------------------------------------------------------- */
button,select,input[type=search],input[type=text]{font:inherit;font-size:var(--t-sm);color:var(--ink);
 background:var(--surface-1);border:1px solid var(--ring-2);border-radius:var(--r-1);padding:4px 9px;
 cursor:pointer;line-height:1.35}
input[type=search],input[type=text],select{cursor:auto}
button:hover,select:hover{border-color:var(--muted)}
button[aria-pressed="true"]{border-color:var(--s1);color:var(--s1);
 background:color-mix(in oklab,var(--s1) 8%,var(--surface-1))}
button:focus-visible,select:focus-visible,input:focus-visible,a:focus-visible,summary:focus-visible,
 [tabindex]:focus-visible{outline:2px solid var(--s1);outline-offset:2px;border-radius:3px}
.iconbtn{padding:4px 8px;font-variant-numeric:tabular-nums}
.bar{display:flex;gap:var(--sp-2);flex-wrap:wrap;align-items:center;margin:var(--sp-2) 0}
.bar .sub{margin-left:auto}

/* --- pills, badges, tiles -------------------------------------------------------------------------------- */
.pills{display:flex;flex-wrap:wrap;gap:var(--sp-1);margin:var(--sp-2) 0}
.pill{border:1px solid var(--ring);border-radius:999px;padding:2px 9px;font-size:var(--t-xs);color:var(--ink-2);
 background:var(--plane);white-space:nowrap}
.pill b{color:var(--ink);font-weight:600}
.badge{border-radius:4px;padding:1px 6px;font-size:var(--t-xs);font-weight:600;border:1px solid var(--ring-2)}
.badge.llm{color:var(--s1);border-color:color-mix(in oklab,var(--s1) 45%,transparent)}
.badge.policy{color:var(--s3);border-color:color-mix(in oklab,var(--s3) 45%,transparent);
 background:repeating-linear-gradient(135deg,transparent 0 3px,color-mix(in oklab,var(--s3) 9%,transparent) 3px 6px)}
.badge.advocate{color:var(--s2);border-color:color-mix(in oklab,var(--s2) 45%,transparent)}

/* the compact summary strip: the whole episode in one row of stats */
.strip{display:flex;flex-wrap:wrap;gap:0;background:var(--surface-1);border:1px solid var(--ring);
 border-radius:var(--r-3);padding:var(--sp-2) 0;margin-bottom:var(--sp-3)}
.strip .stat{padding:2px var(--sp-4);border-right:1px solid var(--grid);min-width:96px}
.strip .stat:last-child{border-right:0}
.strip .k{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
 white-space:nowrap}
.strip .v{font-size:1.15rem;font-weight:600;line-height:1.25;font-variant-numeric:tabular-nums}
.strip .n{font-size:var(--t-xs);color:var(--ink-2)}
.strip .stat.bad .v{color:var(--critical)}

/* --- layout ---------------------------------------------------------------------------------------------- */
.layout{display:grid;grid-template-columns:minmax(0,1fr) 420px;gap:var(--sp-3);align-items:start}
aside{position:sticky;top:calc(var(--topbar) + var(--sp-2));max-height:calc(100vh - var(--topbar) - var(--sp-4));
 overflow-y:auto}
.two{display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-3);align-items:start}
.two>div{min-width:0}

/* --- tables -------------------------------------------------------------------------------------------- */
table{border-collapse:collapse;width:100%;font-size:var(--t-sm);font-variant-numeric:tabular-nums}
th,td{text-align:right;padding:4px 7px;border-bottom:1px solid var(--grid)}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:600;font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.03em}
tbody tr:hover td{background:color-mix(in oklab,var(--ink) 3%,transparent)}
tr.hi td{background:color-mix(in oklab,var(--s1) 12%,transparent)}
.tablewrap{overflow-x:auto}

/* --- disclosure ------------------------------------------------------------------------------------------ */
details{margin:var(--sp-1) 0;border:1px solid var(--ring);border-radius:var(--r-1);background:var(--plane)}
details>summary{cursor:pointer;padding:5px 10px;font-size:var(--t-sm);color:var(--ink-2);list-style:none}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"\\25B8  ";color:var(--muted)}
details[open]>summary::before{content:"\\25BE  "}
details>summary:hover{color:var(--ink)}
details .body{padding:2px 10px 10px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:var(--sp-1) 0;background:var(--surface-1);
 border:1px solid var(--grid);border-radius:var(--r-1);padding:var(--sp-2);font-size:var(--t-sm);
 max-height:460px;overflow:auto}
.msgrole{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
 margin-top:var(--sp-2)}

/* --- charts ---------------------------------------------------------------------------------------------- */
.legend{display:flex;flex-wrap:wrap;gap:var(--sp-3);margin:var(--sp-2) 0 var(--sp-1);font-size:var(--t-sm);
 color:var(--ink-2)}
.legend span{display:flex;align-items:center;gap:5px;white-space:nowrap}
.swatch{width:10px;height:10px;border-radius:50%;border:2px solid var(--surface-1);flex:none}
.swatch.sq{border-radius:2px} .swatch.di{border-radius:2px;transform:rotate(45deg)}
.chartwrap{overflow-x:auto;position:relative}
svg{display:block;max-width:100%;height:auto;touch-action:pan-y}
svg text{fill:var(--ink-2);font-size:11px;font-family:system-ui,sans-serif}
svg .gridline{stroke:var(--grid);stroke-width:1}
svg .axisline{stroke:var(--axis);stroke-width:1}
svg .axistitle{fill:var(--muted);font-size:11px}
svg .lab{fill:var(--ink);font-size:10.5px;font-weight:600;paint-order:stroke;
 stroke:var(--surface-1);stroke-width:3px;stroke-linejoin:round}
svg .dot{fill:var(--muted);opacity:.35}
svg .front{fill:none;stroke:var(--ink-2);stroke-width:1.5;opacity:.75}
svg .envfill{fill:var(--ink-2);opacity:.07}
svg .envline{fill:none;stroke:var(--ink-2);stroke-width:2;opacity:.35}
svg .mark{stroke:var(--surface-1);stroke-width:2;cursor:pointer}
svg .path1{fill:none;stroke:var(--s1);stroke-width:2;opacity:.85}
svg .path2{fill:none;stroke:var(--s2);stroke-width:2;opacity:.85}
svg .mark.ghost{opacity:.3;stroke-width:1}
svg .sel{stroke:var(--ink);stroke-width:2.5}
svg .pinned{stroke:var(--ink);stroke-width:3}
svg.panning{cursor:grabbing}
svg.pannable{cursor:grab}
.zoombar{position:absolute;top:6px;right:6px;display:flex;gap:2px;z-index:3}
.zoombar button{padding:2px 8px;background:color-mix(in oklab,var(--surface-1) 88%,transparent);
 backdrop-filter:blur(2px)}
.detail{margin-top:var(--sp-3);border-top:1px solid var(--grid);padding-top:var(--sp-3);min-height:72px}
.detail .hd{font-weight:600;margin-bottom:var(--sp-1);display:flex;gap:var(--sp-2);align-items:baseline;
 flex-wrap:wrap}
.meter{position:relative;height:8px;background:var(--grid);border-radius:5px;overflow:hidden;display:block}
.meter i{position:absolute;inset:0 auto 0 0;border-radius:5px;display:block}
.meter i.ok{background:var(--s3)} .meter i.bad{background:var(--critical)}
.meter u{position:absolute;top:-2px;bottom:-2px;width:2px;background:var(--ink)}

/* --- the frontier chart's rich hover card (js_hover) -------------------------------------------------------
   One floating element per page, positioned in viewport coordinates beside the pointer. `pointer-events:none`
   while un-pinned is load-bearing: a card that could take the pointer would steal the hover keeping it open.
   Everything is a shared token, so it follows the theme with the rest of the page and prints away cleanly. */
.hcard{position:fixed;left:0;top:0;z-index:60;width:min(360px,calc(100vw - 24px));max-height:min(78vh,560px);
 overflow:auto;pointer-events:none;opacity:0;visibility:hidden;transition:opacity .08s linear;
 background:var(--surface-1);border:1px solid var(--ring-2);border-radius:var(--r-2);
 box-shadow:0 8px 26px rgba(0,0,0,.18),var(--shadow);padding:var(--sp-2) var(--sp-3) var(--sp-1);
 font-size:var(--t-xs);line-height:1.45;color:var(--ink)}
.hcard.on{opacity:1;visibility:visible}
.hcard.pinned{pointer-events:auto;border-color:var(--s1)}
.hcard .hhd{display:flex;gap:var(--sp-2);align-items:baseline;justify-content:space-between;
 font-size:var(--t-sm);font-weight:600}
.hcard .hsub{color:var(--ink-2);margin-top:1px}
.hcard .hnote{margin-top:var(--sp-2);padding:var(--sp-1) var(--sp-2);border-left:2px solid var(--s3);
 background:var(--surface-2);border-radius:0 var(--r-1) var(--r-1) 0;color:var(--ink-2)}
.hcard .hmath{display:block;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:var(--t-xs);
 color:var(--ink);margin-bottom:2px}
.hcard .hmath sub{font-size:.78em}
.hcard .hdeal{margin-top:var(--sp-2);display:flex;flex-wrap:wrap;gap:3px 5px;align-items:baseline}
.hcard .hsep{color:var(--muted)}
.hcard .pills{margin:var(--sp-2) 0 0}
.hcard .hcap{margin-top:var(--sp-2);font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.04em;
 color:var(--muted)}
.hcard table.hrank{width:100%;border-collapse:collapse;font-size:var(--t-xs);
 font-variant-numeric:tabular-nums;margin-top:2px}
.hcard table.hrank th{font-size:.66rem;padding:1px 3px}
.hcard table.hrank td{padding:1px 3px;border-bottom:0}
.hcard table.hrank tbody tr:hover td{background:none}
.hcard .hrk{color:var(--muted);width:1.2em}
.hcard .hnm{max-width:11ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hcard .hnum{text-align:right}
.hcard .hbar{width:54px}
.hcard .hbar .meter{height:6px}
.hcard .hfoot{margin-top:var(--sp-1);color:var(--muted);font-size:.66rem;display:flex;gap:var(--sp-2);
 align-items:center;flex-wrap:wrap}
.hcard .hproj{border-left-color:var(--s2)}
/* the jump control: only clickable on a PINNED card, which is the only time the card takes pointer events */
.hcard .goturn{font-size:.68rem;padding:1px 7px;color:var(--s1);border-color:color-mix(in oklab,var(--s1) 45%,transparent)}
.hcard .goturn:hover{background:color-mix(in oklab,var(--s1) 10%,transparent)}

/* the axis-title info controls: chart chrome until pointed at, and never louder than the axis they annotate */
svg .infodot{cursor:help}
svg .infodot circle{fill:none;stroke:var(--axis);stroke-width:1.2}
svg .infodot text{fill:var(--muted);font-size:9.5px;font-weight:700;font-style:italic}
svg .infodot:hover circle,svg .infodot:focus-visible circle{stroke:var(--s1)}
svg .infodot:hover text,svg .infodot:focus-visible text{fill:var(--s1)}

/* Landing flash: a smooth scroll that ends among thirty near-identical turn cards leaves a reader unsure which
   one they were sent to, so the destination says so for a moment. Motion-free fallback keeps the tint. */
@keyframes turnflash{0%{background:color-mix(in oklab,var(--s1) 22%,transparent)}
 100%{background:transparent}}
.turn.flash{animation:turnflash 1.2s ease-out 1}
@media (prefers-reduced-motion:reduce){.turn.flash{animation:none;
 background:color-mix(in oklab,var(--s1) 12%,transparent)}}

/* --- transcript: the turn-type visual grammar -------------------------------------------------------------
   Action types are STATES, so they wear the reserved status palette, never a categorical series slot — and every
   one of them carries a glyph and a word beside the colour, so nothing is colour-alone. */
.turn{border:1px solid var(--ring);border-left:3px solid var(--grid);border-radius:var(--r-2);
 background:var(--surface-1);padding:10px 13px;margin-bottom:var(--sp-2);scroll-margin-top:calc(var(--topbar) + var(--scrubh) + var(--sp-3))}
.turn.a-propose{border-left-color:var(--s1)}
.turn.a-accept{border-left-color:var(--good)}
.turn.a-reject{border-left-color:var(--serious)}
.turn.a-walk{border-left-color:var(--critical)}
.turn.a-vote{border-left-color:var(--s3)}
.turn.a-talk,.turn.a-none{border-left-color:var(--axis)}
.turn.k-policy{border-left-style:dashed}
.turn.divergent{box-shadow:inset 3px 0 0 var(--s2),0 0 0 1px var(--s2)}
.turn.fabricated{border-left-color:var(--critical);
 background:color-mix(in oklab,var(--critical) 6%,var(--surface-1))}
.turn.sel{box-shadow:0 0 0 2px var(--s1)}
.badge.fabricated{color:var(--critical);border-color:var(--critical);font-weight:700}
.fabnote{border-color:var(--critical);color:var(--ink)}
.turnhd{display:flex;justify-content:space-between;gap:var(--sp-2);align-items:baseline;flex-wrap:wrap;
 position:sticky;top:calc(var(--topbar) + var(--scrubh) - 1px);z-index:5;background:inherit;
 margin:-10px -13px var(--sp-1);
 padding:8px 13px 6px;border-radius:var(--r-2) var(--r-2) 0 0;cursor:pointer}
.turnhd .who{font-weight:600;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.turnhd .idx{color:var(--muted);font-variant-numeric:tabular-nums;font-weight:600}
.kind{font-size:var(--t-xs);font-weight:600;letter-spacing:.03em;padding:1px 7px;border-radius:999px;
 border:1px solid currentColor;white-space:nowrap}
.kind.a-propose{color:var(--s1)} .kind.a-accept{color:var(--good)} .kind.a-reject{color:var(--serious)}
.kind.a-walk{color:var(--critical)} .kind.a-vote{color:var(--s3)}
.kind.a-talk,.kind.a-none{color:var(--muted)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-2);margin-top:var(--sp-2)}
.col{border:1px solid var(--grid);border-radius:var(--r-1);padding:8px 10px;background:var(--plane)}
.col .hd{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
 margin-bottom:3px}
.col.acted{border-top:2px solid var(--s1)} .col.oracle{border-top:2px solid var(--s2)}
.act{font-weight:600;font-size:var(--t-md)}
.deal{font-size:var(--t-sm);color:var(--ink-2);margin-top:3px}
.msg{border-left:3px solid var(--grid);padding-left:9px;margin:var(--sp-2) 0;font-size:var(--t-md)}
.gap{border:1px dashed var(--axis);border-radius:var(--r-1);padding:8px 10px;font-size:var(--t-sm);
 color:var(--ink-2);background:var(--plane)}

/* the turn scrubber: every turn as one chip, coloured by action type, fabricated ones ringed. One row that
   scrolls sideways rather than wrapping — a sticky element whose height depends on the turn count would push the
   whole stack around as a run gets longer. */
.scrub{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:3px;padding:5px 0;position:sticky;
 top:calc(var(--topbar) - 1px);z-index:10;height:var(--scrubh);background:var(--surface-1);
 border-bottom:1px solid var(--grid);margin-bottom:var(--sp-2);scrollbar-width:thin}
.chip{flex:none}
.chip{font-size:var(--t-xs);font-variant-numeric:tabular-nums;min-width:22px;text-align:center;padding:1px 4px;
 border-radius:4px;border:1px solid var(--ring-2);color:var(--ink-2);background:var(--plane);cursor:pointer;
 border-bottom-width:3px}
.chip.a-propose{border-bottom-color:var(--s1)} .chip.a-accept{border-bottom-color:var(--good)}
.chip.a-reject{border-bottom-color:var(--serious)} .chip.a-walk{border-bottom-color:var(--critical)}
.chip.a-vote{border-bottom-color:var(--s3)}
.chip.fab{border-color:var(--critical);color:var(--critical);font-weight:700}
.chip.cur{background:var(--s1);color:#fff;border-color:var(--s1)}
.chip:hover{border-color:var(--ink)}

/* --- comparison ------------------------------------------------------------------------------------------ */
.colhd{font-weight:600;padding:6px 10px;border-radius:var(--r-1);background:var(--surface-2);
 border:1px solid var(--ring);margin-bottom:var(--sp-2);position:sticky;top:calc(var(--topbar) - 1px);z-index:12;
 height:var(--colhdh);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* inside a comparison column the stack gains a layer, so both the ones below it move down by its height */
.two .scrub{top:calc(var(--topbar) + var(--colhdh) - 1px)}
.two .turnhd{top:calc(var(--topbar) + var(--colhdh) + var(--scrubh) - 1px)}
.colhd.a{border-top:3px solid var(--s1)} .colhd.b{border-top:3px solid var(--s2)}
.divmark{border-top:2px dashed var(--s2);color:var(--s2);font-size:var(--t-sm);font-weight:600;
 text-align:center;margin:var(--sp-4) 0;padding-top:5px}
.verdict{display:flex;flex-wrap:wrap;gap:var(--sp-2);align-items:center;padding:var(--sp-2) var(--sp-3);
 border:1px solid var(--ring);border-radius:var(--r-2);background:var(--surface-1);margin-bottom:var(--sp-3)}
.verdict .hd{font-weight:600;font-size:var(--t-md)}
.verdict .won{font-weight:600}
.verdict .won.l{color:var(--s1)} .verdict .won.r{color:var(--s2)}

/* --- notices --------------------------------------------------------------------------------------------- */
.warn{border-left:4px solid var(--warn);padding:8px 12px;background:var(--surface-1);border-radius:var(--r-1);
 font-size:var(--t-md);margin-bottom:var(--sp-2)}
.warn b{color:var(--ink)}
.warn.danger{border-left-color:var(--critical)}

/* --- index: filter row above one sortable table ---------------------------------------------------------- */
.filterbar{display:flex;gap:var(--sp-2);flex-wrap:wrap;align-items:center;margin-bottom:var(--sp-3)}
.filterbar input[type=search]{min-width:230px;flex:1 1 230px}
.filterbar .count{color:var(--ink-2);font-size:var(--t-sm);font-variant-numeric:tabular-nums;margin-left:auto}
table.sortable th[data-sort]{cursor:pointer;user-select:none;white-space:nowrap}
table.sortable th[data-sort]:hover{color:var(--ink)}
table.sortable th[aria-sort]{color:var(--s1)}
table.sortable th[aria-sort="ascending"]::after{content:" \\2191"}
table.sortable th[aria-sort="descending"]::after{content:" \\2193"}
tr[hidden]{display:none}
.inlinebar{display:inline-block;vertical-align:middle;width:52px;height:6px;border-radius:3px;
 background:var(--grid);margin-left:6px;position:relative;overflow:hidden}
.inlinebar i{position:absolute;inset:0 auto 0 0;background:var(--s1);border-radius:3px}
.inlinebar.warnfill i{background:var(--critical)}
td .flag{color:var(--critical);font-weight:600}

/* --- help overlay ---------------------------------------------------------------------------------------- */
#help[hidden]{display:none}
#help{position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.45);display:flex;align-items:center;
 justify-content:center;padding:var(--sp-4)}
#help .panel{background:var(--surface-1);border:1px solid var(--ring-2);border-radius:var(--r-3);
 padding:var(--sp-5);max-width:620px;width:100%;max-height:86vh;overflow:auto;box-shadow:0 8px 40px rgba(0,0,0,.3)}
#help table{font-size:var(--t-md)}
#help td:first-child{width:130px}
.skip{position:absolute;left:-9999px}
.skip:focus{left:var(--sp-2);top:var(--sp-2);z-index:200;position:fixed;background:var(--surface-1);
 padding:var(--sp-2);border:1px solid var(--s1);border-radius:var(--r-1)}

/* --- the tabbed sidebar ------------------------------------------------------------------------------------
   One sticky column carrying four views of the same episode. The tab strip is fixed inside it and the active
   pane is the only thing that scrolls, so the tabs never scroll away from a reader halfway down a long game
   panel. Panes are plain hidden sections, so the sidebar still reads with scripting off. */
aside.sidebar{display:flex;flex-direction:column;gap:0;padding:0;overflow:hidden;
 background:var(--surface-1);border:1px solid var(--ring);border-radius:var(--r-3)}
.sidebar .tabs{display:flex;flex:none;gap:2px;padding:var(--sp-2) var(--sp-2) 0;border-bottom:1px solid var(--grid);
 background:var(--surface-1);overflow-x:auto;scrollbar-width:thin}
.sidebar .tab{flex:none;border:1px solid transparent;border-bottom:0;border-radius:var(--r-1) var(--r-1) 0 0;
 background:transparent;color:var(--ink-2);padding:5px 10px;margin-bottom:-1px;white-space:nowrap}
.sidebar .tab[aria-selected="true"]{color:var(--ink);font-weight:600;background:var(--plane);
 border-color:var(--ring);border-bottom:1px solid var(--plane)}
.sidebar .syncline{flex:none;padding:4px var(--sp-3);border-bottom:1px solid var(--grid);font-size:var(--t-xs);
 font-variant-numeric:tabular-nums}
.sidebar .pane{flex:1 1 auto;overflow-y:auto;padding:var(--sp-3);min-height:0}
.sidebar .pane[hidden]{display:none}
.sidebar .card{border:0;border-bottom:1px solid var(--grid);border-radius:0;padding:var(--sp-2) 0;
 margin-bottom:var(--sp-2);background:transparent}
.sidebar .card:last-child{border-bottom:0}

/* the conversation view: the seat in view speaks on the right, everyone else on the left */
.chatlog{display:flex;flex-direction:column;gap:var(--sp-2);margin-top:var(--sp-2)}
.bubble{max-width:88%;border:1px solid var(--ring);border-radius:var(--r-2) var(--r-2) var(--r-2) 2px;
 background:var(--surface-2);padding:6px 9px;font-size:var(--t-sm);scroll-margin:var(--sp-4) 0}
.bubble .who{display:flex;align-items:baseline;gap:5px;font-weight:600;font-size:var(--t-xs);color:var(--ink-2)}
.bubble .who .pidx{color:var(--muted);font-variant-numeric:tabular-nums}
.bubble .who .at{margin-left:auto;font-weight:400;color:var(--muted);white-space:nowrap}
.bubble .body{margin-top:3px;white-space:pre-wrap;overflow-wrap:anywhere}
.bubble .chipline{margin-top:5px}
.bubble.self{margin-left:auto;border-radius:var(--r-2) var(--r-2) 2px var(--r-2);
 background:color-mix(in oklab,var(--s1) 10%,var(--surface-1));border-color:color-mix(in oklab,var(--s1) 35%,var(--ring))}
.bubble.self .who::before{content:"\\2190 in view  ";color:var(--s1);font-weight:600}
.bubble.future{opacity:.42}
.bubble.cur{box-shadow:0 0 0 2px var(--s1)}
.bubble.fab{border-color:var(--critical)}
.bubble .fabtag{margin-top:4px;font-size:var(--t-xs);font-weight:700;color:var(--critical)}
.actchip{display:inline-block;font-size:var(--t-xs);border:1px solid currentColor;border-radius:999px;
 padding:1px 8px;color:var(--muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.actchip b{font-weight:700}
.actchip.a-propose{color:var(--s1);border-radius:var(--r-1)}
.actchip.a-accept{color:var(--good)} .actchip.a-reject{color:var(--serious)}
.actchip.a-walk{color:var(--critical)} .actchip.a-vote{color:var(--s3)}

/* contextual help: a compact circular control links measurements to the long-form Info tab */
.infobtn{display:inline-grid;place-items:center;width:16px;height:16px;min-width:16px;padding:0;margin-left:3px;
 border:1px solid currentColor;border-radius:50%;background:transparent;color:var(--ink-2);font:700 10px/1 serif;
 vertical-align:1px}
.infobtn:hover,.infobtn:focus-visible{color:var(--s1);background:color-mix(in oklab,var(--s1) 8%,transparent)}
.infosection{padding:0 0 var(--sp-3);margin:0 0 var(--sp-3);border-bottom:1px solid var(--grid)}
.infosection:last-child{border-bottom:0;margin-bottom:0}.infosection h2{font-size:var(--t-md);margin:0 0 var(--sp-1)}
.infosection p{font-size:var(--t-sm);color:var(--ink-2);margin:0 0 var(--sp-2)}
.infointro{font-size:var(--t-sm);margin-bottom:var(--sp-3)}
.formula{padding:var(--sp-2);margin:var(--sp-2) 0;background:var(--surface-2);border-left:2px solid var(--s2);
 border-radius:0 var(--r-1) var(--r-1) 0;text-align:center;overflow-x:auto;font-size:var(--t-md);white-space:nowrap}

/* the per-agent issue view */
.issueseat .hd{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap;font-weight:600;margin-bottom:var(--sp-1)}
.issueseat .hd .muted{font-weight:400;font-size:var(--t-xs)}
svg.issuesvg .track{fill:color-mix(in oklab,var(--ink) 4%,transparent);stroke:var(--grid)}
svg.issuesvg .opt{stroke:var(--ink-2);stroke-width:2;opacity:.8}
svg.issuesvg .opt:hover{stroke:var(--ink);stroke-width:3}
svg.issuesvg .taul{stroke:var(--ink-2);stroke-width:1.5;stroke-dasharray:5 4;opacity:.85}
svg.issuesvg .taulab{fill:var(--muted);font-size:10px}
svg.issuesvg .issuelab{fill:var(--ink-2);font-size:10px}
svg.issuesvg .dealmark{stroke:var(--s1);stroke-width:4;stroke-linecap:round}
svg.issuesvg .dealdot{fill:var(--s1);stroke:var(--surface-1);stroke-width:1.5}
.legend .swatch.tick{width:12px;height:2px;border-radius:0;border:0;background:var(--ink-2)}
.legend .swatch.line{width:12px;height:4px;border-radius:2px;border:0;background:var(--s1)}
.legend .swatch.dash{width:12px;height:0;border:0;border-top:2px dashed var(--ink-2);border-radius:0}
.issuenums{display:flex;flex-wrap:wrap;gap:var(--sp-1);margin-top:var(--sp-2);font-variant-numeric:tabular-nums}

/* --- responsive / print ---------------------------------------------------------------------------------- */
@media (max-width:1180px){.layout{grid-template-columns:1fr}
 aside{position:static;max-height:none}
 aside.sidebar{overflow:visible}
 .sidebar .pane{max-height:none;overflow:visible}}
@media (max-width:760px){.cols,.two{grid-template-columns:1fr}
 .topbar{position:static} .turnhd,.scrub,.colhd{position:static} main{padding:var(--sp-3)}
 .strip .stat{border-right:0}}
@media print{aside,button,select,.topbar,.scrub,.zoombar,#help,.hcard{display:none}
 .card{break-inside:avoid;border:1px solid #ccc} .turn{break-inside:avoid}}
"""
