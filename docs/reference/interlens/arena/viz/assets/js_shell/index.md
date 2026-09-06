# `js_shell`

Module `interlens.arena.viz.assets.js_shell`

Browser layer, part 4: the page shell — theme toggle, episode navigation, keyboard shortcuts, help overlay.

Every page kind (episode, comparison, index) wears the same shell, so a reader learns the controls once. Three
pieces:

**Theme.** The stylesheet declares dark twice — under the OS media query and under a `data-theme` stamp — and
this is what does the stamping, remembering the choice in `localStorage` where that is allowed. It is wrapped
in a `try` because a page opened over `file://` may have storage denied outright, and a viewer losing their
theme preference must never cost them the page.

**Navigation.** Prev/next links and the episode picker are plain `<a>` and `<select>` elements rendered
server-side, so they work with scripting off; this only adds the keyboard bindings and the picker's jump.

**Shortcuts.** `registerKeys` takes a map and does the two things every such map gets wrong: it ignores
keystrokes aimed at a text field or a `<select>`, and it leaves modified keystrokes (Ctrl/⌘/Alt) alone so
browser and OS shortcuts still work. The help overlay is generated from the SAME map, so a binding cannot exist
without being documented.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_SHELL` |  |  |
