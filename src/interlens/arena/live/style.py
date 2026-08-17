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
# [implement: live-play/laneE] 2026-08-17
"""The rules the lobby and the play page both need: form controls, seat cards, and the two docks.

Live play is the only part of the visualizer with FORMS in it — everything else renders numbers and prose — so
the shared stylesheet (``viz.assets.CSS``) styles no input, select or textarea, and both live pages would
otherwise carry their own copy of the same handful of rules. They are here instead, in the vocabulary of the
shared sheet's own tokens (``--surface-1``, ``--ring``, ``--sp-3``), so a live control looks like part of the
same page as the transcript beside it and a change to either page's controls is one edit rather than two.

Page-specific layout stays on the page that owns it (the lobby's start bar and problem lists, for instance);
what is here is what a seat card, a labelled field and a dock are on both.
"""
from __future__ import annotations

#: Form controls and the two seat-card grids, inlined by ``render_lobby_html`` and ``render_live_html``.
CSS_LIVE = """
.field{display:flex;flex-direction:column;gap:3px;min-width:0}
.field>label{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:600}
.field>.hint{font-size:var(--t-xs);color:var(--muted);line-height:1.35}
.field.off{opacity:.45}
.field .req{color:var(--critical);font-weight:700}
textarea,input[type=number],input[type=text]{font:inherit;font-size:var(--t-sm);color:var(--ink);
 background:var(--surface-1);border:1px solid var(--ring-2);border-radius:var(--r-1);padding:4px 8px;width:100%}
textarea{min-height:4.4em;resize:vertical;line-height:1.4}
select:disabled,input:disabled,textarea:disabled{opacity:.5;cursor:not-allowed}
select,input[type=text],input[type=number]{width:100%}
.seatcard{border:1px solid var(--ring);border-radius:var(--r-2);padding:var(--sp-3);background:var(--plane);
 display:flex;flex-direction:column;gap:var(--sp-2)}
.seatcard>.hd{display:flex;align-items:baseline;gap:var(--sp-2);justify-content:space-between;flex-wrap:wrap}
.seatcard>.hd .who{font-weight:600;font-size:var(--t-md)}

/* The player's dock. Dimmed until the seat is actually being asked for a move, so "is it my turn" is answerable
   from across the room rather than by reading which buttons are enabled. */
.dock{opacity:.72}
.dock.open{opacity:1;border-color:var(--s1)}
.dock #dock-error:not(:empty){margin:var(--sp-2) 0;color:var(--critical);font-size:var(--t-sm)}
.offerbuild{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:var(--sp-2);
 margin:var(--sp-2) 0}
.dock label.sub{display:flex;flex-direction:column;gap:3px;margin-top:var(--sp-2)}
.dock .bar{margin-top:var(--sp-3);flex-wrap:wrap}

/* The swap dock: the same seat card, one per seat, with the current occupant badged in its header. */
.seatswaps{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:var(--sp-3);
 margin-top:var(--sp-2)}
.seatswap{border:1px solid var(--ring);border-radius:var(--r-2);padding:var(--sp-2);background:var(--plane);
 display:flex;flex-direction:column;gap:4px}
.seatswap>.hd{font-weight:600;display:flex;gap:var(--sp-2);align-items:baseline;flex-wrap:wrap}
.seatswap label.sub{display:flex;flex-direction:column;gap:2px}
.seatswap [id^=swap-error]:not(:empty){color:var(--critical)}
"""

__all__ = ["CSS_LIVE"]
