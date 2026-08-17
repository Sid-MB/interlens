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
# [implement: live-play/lane0] 2026-08-16
"""The live pages' browser layer, as Python strings — same convention as ``viz.assets``.

Only the LIVE parts live here. The chart, hover cards, transcript cards, sidebar and page shell are imported from
``viz.assets`` unchanged: a live page is the episode page plus an update path, and reimplementing any of the
visualizer in a second copy is how the two would start disagreeing about what the same episode looks like.

No external assets, no build step, no CDN — the pages must work on a cluster node behind a firewall.
"""
from __future__ import annotations

from .js_live import JS_LIVE
from .js_lobby import JS_LOBBY

__all__ = ["JS_LIVE", "JS_LOBBY"]
