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

"""Browser layer, part 4: the page shell — theme toggle, episode navigation, keyboard shortcuts, help overlay.

Every page kind (episode, comparison, index) wears the same shell, so a reader learns the controls once. Three
pieces:

**Theme.** The stylesheet declares dark twice — under the OS media query and under a ``data-theme`` stamp — and
this is what does the stamping, remembering the choice in ``localStorage`` where that is allowed. It is wrapped
in a ``try`` because a page opened over ``file://`` may have storage denied outright, and a viewer losing their
theme preference must never cost them the page.

**Navigation.** Prev/next links and the episode picker are plain ``<a>`` and ``<select>`` elements rendered
server-side, so they work with scripting off; this only adds the keyboard bindings and the picker's jump.

**Shortcuts.** ``registerKeys`` takes a map and does the two things every such map gets wrong: it ignores
keystrokes aimed at a text field or a ``<select>``, and it leaves modified keystrokes (Ctrl/⌘/Alt) alone so
browser and OS shortcuts still work. The help overlay is generated from the SAME map, so a binding cannot exist
without being documented.
"""
from __future__ import annotations

JS_SHELL = r"""
/* ---- theme: stamp data-theme so the viewer's choice beats the OS setting, in both directions ---- */
(function () {
  const KEY = "interlens-viz-theme";
  const read = () => { try { return localStorage.getItem(KEY); } catch (e) { return null; } };
  const write = (v) => { try { localStorage.setItem(KEY, v); } catch (e) { /* file:// may deny storage */ } };
  const saved = read();
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  const btn = $("theme-toggle");
  const paint = () => {
    if (!btn) return;
    const dark = document.documentElement.getAttribute("data-theme") === "dark"
      || (!document.documentElement.getAttribute("data-theme")
          && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    btn.textContent = dark ? "☀" : "☾";
    btn.title = dark ? "Switch to the light theme" : "Switch to the dark theme";
  };
  if (btn) btn.addEventListener("click", () => {
    const dark = document.documentElement.getAttribute("data-theme") === "dark"
      || (!document.documentElement.getAttribute("data-theme")
          && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    write(next); paint();
  });
  paint();
})();

/* ---- episode picker: a plain <select> of sibling pages ---- */
(function () {
  const picker = $("ep-picker");
  if (picker) picker.addEventListener("change", () => { if (picker.value) location.href = picker.value; });
})();

function goSibling(rel) {          // rel: "prev" | "next" — follows the server-rendered nav link if there is one
  const a = document.querySelector(`a[data-nav="${rel}"]:not(.disabled)`);
  if (a) location.href = a.getAttribute("href");
}

/* ---- keyboard: one map drives both the handler and the help overlay ---- */
function registerKeys(bindings) {
  const typing = (t) => t && (t.isContentEditable
    || ["INPUT", "TEXTAREA", "SELECT", "OPTION"].includes(t.tagName));
  document.addEventListener("keydown", (ev) => {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;   // never shadow a browser or OS shortcut
    if (typing(ev.target) && ev.key !== "Escape") return;
    const b = bindings.find(b => b.keys.includes(ev.key));
    if (!b) return;
    ev.preventDefault();
    b.run(ev);
  });
  const help = $("help");
  if (help) {
    const body = help.querySelector("tbody");
    if (body) body.innerHTML = bindings.filter(b => b.what).map(b =>
      `<tr><td>${b.keys.filter(k => k !== "Escape" || b.keys.length === 1)
        .map(k => `<kbd>${E(k === " " ? "space" : k)}</kbd>`).join(" ")}</td><td>${E(b.what)}</td></tr>`).join("");
    help.addEventListener("click", (ev) => { if (ev.target === help) help.hidden = true; });
    const close = help.querySelector("[data-close]");
    if (close) close.addEventListener("click", () => { help.hidden = true; });
  }
  const btn = $("help-toggle");
  if (btn && help) btn.addEventListener("click", () => { help.hidden = !help.hidden; });
}

/* The bindings every page shares. A page appends its own and passes the whole list to registerKeys, so the help
   overlay always lists exactly what is bound on THAT page. */
function shellKeys() {
  const help = $("help");
  return [
    { keys: ["n"], what: "next episode", run: () => goSibling("next") },
    { keys: ["p"], what: "previous episode", run: () => goSibling("prev") },
    { keys: ["u"], what: "up to the run index", run: () => { const a = document.querySelector('a[data-nav="index"]'); if (a) location.href = a.getAttribute("href"); } },
    { keys: ["?"], what: "show or hide this help", run: () => { if (help) help.hidden = !help.hidden; } },
    { keys: ["Escape"], what: "", run: () => { if (help) help.hidden = true; } },
  ];
}
"""
