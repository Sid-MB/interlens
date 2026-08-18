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

"""The inline stylesheet and browser layer — no external assets of any kind.

Every generated page is opened straight off a filesystem path (``file://``), often on a cluster login node behind
no web server, so a single request to a CDN would leave the chart blank. The CSS and JS therefore live here as
Python strings that get inlined into the HTML.

The layer is assembled from small pieces rather than one string, because they have genuinely different jobs and
different pages want different subsets — the run index carries no episode payload, so it loads the utilities and
the shell and none of the data layer:

===================  =========================================================================================
module               what it holds
===================  =========================================================================================
``css``              the design system: tokens, light/dark, the action-type grammar, layout, controls
``js_core``          ``JS_UTIL`` (formatting + DOM helpers) and ``JS_CORE`` (payload, view rehydration, deals)
``js_hover``         the rich hover card every chart point carries, incl. the solution-concept explanations
``js_chart``         the frontier chart (hover, pin, zoom/pan) and the regret strip
``js_transcript``    turn cards, the scrubber, lazily-built prompt bodies, turn selection
``js_sidebar``       the tabbed sidebar and the IntersectionObserver scroll sync that drives it
``js_shell``         theme toggle, episode navigation, keyboard bindings, the help overlay
``js_episode``       the episode page's wiring
``js_auction``       the auction episode page's wiring (stage scrubber, ladder hover, transcript sync)
``js_compare``       the comparison page's wiring
``js_index``         the run index's sort and filter
===================  =========================================================================================

``JS`` is the bundle every data page shares (utilities, data layer, charts, transcript, shell), so a page's own
script is only its wiring. ``JS_INDEX_PAGE`` is the index's smaller bundle.

**Colour.** Both modes are explicitly selected, not derived by flipping the light values, and the categorical
slots are capped at THREE. That cap is the binding constraint of the colour formula for a scatter: with all pairs
of series simultaneously on screen (which is what a scatter does, unlike a bar chart's adjacent pairs), only the
first three slots clear the colour-blindness and normal-vision separation floors in both modes. The three slots
carry the only three identities that must be told apart by colour:

============  =========================  ==========================
slot          episode page               comparison page
============  =========================  ==========================
1 (blue)      what the model actually did the left episode
2 (orange)    what the oracle recommends  the right episode
3 (aqua)      normative solution points   normative solution points
============  =========================  ==========================

Everything else is encoded by **shape plus a direct label**: NBS, KS, and EGAL are aqua stars; UTIL and MNW are
violet triangles; every concept is directly labelled on the chart. Violet is a redundant reference-point accent,
not a fourth trajectory identity—the triangle and labels carry the distinction without colour. The per-party
ideal points share one aqua diamond with the party named on hover and enumerated in the side panel's table. Deals themselves are chart chrome,
not a series: dominated deals are muted dots, frontier deals carry the secondary-ink ring. Slot 3 sits below 3:1
against the light surface, which obligates the relief rule — hence the always-visible direct labels and the
numeric table view that every chart ships with. Action types on the transcript are STATES rather than a series, so
they wear the reserved status palette and always carry a glyph and a word beside the colour.
"""
from __future__ import annotations

from .css import CSS
from .js_auction import JS_AUCTION
from .js_chart import JS_CHART
from .js_compare import JS_COMPARE
from .js_core import JS_CORE, JS_UTIL
from .js_episode import JS_EPISODE
from .js_hover import JS_HOVER
from .js_index import JS_INDEX
from .js_shell import JS_SHELL
from .js_sidebar import JS_SIDEBAR
from .js_transcript import JS_TRANSCRIPT

#: Everything a data page (episode or comparison) needs before its own wiring runs. The sidebar layer is a no-op
#: on a page that carries no ``#sidebar`` element, which is what makes it safe in the shared bundle.
JS = "\n".join((JS_UTIL, JS_CORE, JS_HOVER, JS_CHART, JS_TRANSCRIPT, JS_SIDEBAR, JS_SHELL))

#: The run index's bundle: the same shell and helpers, none of the episode data layer.
JS_INDEX_PAGE = "\n".join((JS_UTIL, JS_SHELL, JS_INDEX))

__all__ = ["CSS", "JS", "JS_AUCTION", "JS_CHART", "JS_COMPARE", "JS_CORE", "JS_EPISODE", "JS_HOVER",
           "JS_INDEX", "JS_INDEX_PAGE", "JS_SHELL", "JS_SIDEBAR", "JS_TRANSCRIPT", "JS_UTIL"]
