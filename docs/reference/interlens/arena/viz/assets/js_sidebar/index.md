# `interlens.arena.viz.assets.js_sidebar`

Browser layer, part 5: the tabbed sidebar and the scroll sync that drives it.

The sidebar's three live tabs all answer the same question — *what did the table look like at the point in the
transcript I am reading?* — so they share one piece of state: the turn currently in the viewport, tracked with an
`IntersectionObserver` over the turn cards rather than a scroll handler (no per-frame work, and the browser
does the geometry).

- **Conversation** re-anchors the public chat to the acting seat: that seat's bubbles move to the right, everyone
  else's stay left, and the list scrolls itself so the turn being read is the one in the middle. The bubbles are
  rendered server-side and never rebuilt — the point of view is two class toggles.
- **Frontier** redraws the main chart's geometry restricted to what had been proposed by that turn: earlier
  proposals numbered, the deal standing on the table squared, later ones ghosted. It is drawn through the SAME
  `frontierChart` the page's main chart uses, so the two cannot drift apart.
- **Issues** shows the acting seat's private valuation of each issue, with a marker on the option the deal on the
  table picks. The bars, ticks and threshold line come from the server-rendered SVG; the marker is placed by
  reading each tick's own `data-y`, so the browser never re-derives the scale.
- **Info** is a standing reading guide. Inline information buttons open it directly at the oracle explanation.

The seat shown in the issue tab can be pinned with the picker; the next time scrolling changes which turn is in
view the pin is released, because a pin that silently survived a scroll is how a reader ends up reading one
seat's bars believing they are another's.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_SIDEBAR` |  |  |
