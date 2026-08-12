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
# [rational_agents: viz-ux] 2026-08-03

"""The run index's browser layer: sort and filter, over the rows already in the document.

Deliberately **not** payload-driven. The rows are rendered server-side as a real table — every number visible with
scripting off — and sorting reads a ``data-sort`` attribute off each cell rather than a parallel JSON copy of the
same data. A hundred-episode index therefore costs one table, not a table plus its duplicate.

Filtering is a text match across the row plus two chips (deal / no deal, has fabricated turns), and the count of
what survives is always on screen, because a filter that silently hides rows is how a reader concludes a run has
fewer episodes than it does.
"""
from __future__ import annotations

JS_INDEX = r"""
const table = document.querySelector("table.sortable");
const tbody = table ? table.querySelector("tbody") : null;
const rows = tbody ? Array.from(tbody.children) : [];
const search = $("idx-search"), count = $("idx-count");
let outcomeFilter = "", flagFilter = "";

/* Sort on the cell's data-sort value (numeric when it parses, text otherwise), never on the rendered string —
   "1.0" and "10.0" sort wrong as text, and an em-dash for a missing number must sink rather than sort as zero. */
function sortBy(th) {
  const idx = Array.from(th.parentNode.children).indexOf(th);
  const asc = th.getAttribute("aria-sort") !== "ascending";
  table.querySelectorAll("th[aria-sort]").forEach(o => o.removeAttribute("aria-sort"));
  th.setAttribute("aria-sort", asc ? "ascending" : "descending");
  const key = (r) => {
    const cell = r.children[idx];
    const raw = cell ? (cell.dataset.sort !== undefined ? cell.dataset.sort : cell.textContent.trim()) : "";
    const n = parseFloat(raw);
    return (raw !== "" && !isNaN(n) && /^-?[\d.eE+]+$/.test(raw)) ? n : raw.toLowerCase();
  };
  const missing = (v) => v === "" || v === "—";
  rows.slice().sort((a, b) => {
    const ka = key(a), kb = key(b);
    if (missing(ka) !== missing(kb)) return missing(ka) ? 1 : -1;    // absent values always sink
    if (ka < kb) return asc ? -1 : 1;
    if (ka > kb) return asc ? 1 : -1;
    return 0;
  }).forEach(r => tbody.appendChild(r));
}
if (table) table.querySelectorAll("th[data-sort]").forEach(th => {
  th.tabIndex = 0;
  th.addEventListener("click", () => sortBy(th));
  th.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); sortBy(th); } });
});

function applyFilter() {
  const q = (search && search.value || "").trim().toLowerCase();
  let shown = 0;
  rows.forEach(r => {
    const hay = (r.dataset.hay || r.textContent).toLowerCase();
    const ok = (!q || hay.includes(q))
      && (!outcomeFilter || r.dataset.deal === outcomeFilter)
      && (!flagFilter
          || (flagFilter === "fabricated" && Number(r.dataset.fabricated || 0) > 0)
          /* Wider than `fabricated`, and deliberately a separate control: a spoiled vintage, a non-default token
             budget, and a silent episode are all reasons a row's numbers do not pair with another row's, and
             none of them makes the engine fabricate a turn. */
          || (flagFilter === "hazards" && Number(r.dataset.hazards || 0) > 0));
    r.hidden = !ok;
    if (ok) shown++;
  });
  if (count) count.textContent = shown === rows.length
    ? `${rows.length} page${rows.length === 1 ? "" : "s"}`
    : `${shown} of ${rows.length} shown`;
}
if (search) search.addEventListener("input", applyFilter);
document.querySelectorAll("[data-filter]").forEach(b => b.addEventListener("click", () => {
  const [kind, value] = b.dataset.filter.split(":");
  const target = kind === "outcome" ? "outcomeFilter" : "flagFilter";
  const on = b.getAttribute("aria-pressed") !== "true";
  document.querySelectorAll(`[data-filter^="${kind}:"]`).forEach(o => o.setAttribute("aria-pressed", "false"));
  b.setAttribute("aria-pressed", String(on));
  if (target === "outcomeFilter") outcomeFilter = on ? value : "";
  else flagFilter = on ? value : "";
  applyFilter();
}));
applyFilter();

registerKeys([
  { keys: ["/"], what: "focus the filter box", run: () => { if (search) { search.focus(); search.select(); } } },
  { keys: ["Escape"], what: "clear the filter", run: () => { if (search && search.value) { search.value = ""; applyFilter(); } const h = $("help"); if (h) h.hidden = true; } },
  { keys: ["?"], what: "show or hide this help", run: () => { const h = $("help"); if (h) h.hidden = !h.hidden; } },
  { keys: ["Enter"], what: "open the first row that survives the filter", run: () => {
      const first = rows.find(r => !r.hidden);
      const a = first && first.querySelector("a[href]");
      if (a) location.href = a.getAttribute("href");
    } },
]);
"""
