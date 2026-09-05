# `interlens.arena.live.assets.js_lobby`

The lobby's browser layer: edit the seat lineup, then start the game.

Every edit is POSTed to `/api/lobby` and the server's response is what the page re-renders from — the server
owns the configuration, the page never keeps its own copy. That is what makes a second browser tab on the lobby
show the same lineup instead of a private one, and it means the validation that matters (does this model exist,
does it accept this thinking mode) happens where the provider is.

`/api/start` returns the session id; the page then navigates to `/play`, which is rendered server-side from
the session's snapshot.

Three things are worth knowing before reading the script:

**It edits controls, it does not build them.** Seat cards are rendered once, in Python
(`lobby_page._seat_card`). This layer sets values, toggles `disabled`, and rebuilds two option lists that
genuinely depend on another choice — the thinking modes a newly picked model allows, and the instances a newly
picked bank contains. When an edit changes the page's SHAPE (a bank with a different party count, so a different
number of cards) it reloads and lets the server render it. A JavaScript copy of the card markup is the fast way
to end up with two lobbies that disagree about what a seat is.

**Field names live in one map.** :js:data:`SEAT_FIELDS` and :js:data:`LOBBY_FIELDS` are the only place this file
spells a state key, and they are exactly the `data-field` / `data-lobby` attributes the markup carries and
exactly `SeatConfig`'s dataclass fields. The lobby test pins all three to each other, so a renamed field fails
a test instead of silently editing nothing.

**Defaults are computed, never typed.** Which model a new LLM seat opens on and which thinking mode it takes come
from `defaultModelId` / `defaultThinking`, mirroring `provider.default_model_id` /
`provider.default_thinking` — the provider flags its default model, so no model id is spelled in this file. The
"all model seats" row writes those same fields into many seats at once (`applyAll`) and then saves through the
ordinary whole-seats POST, which is why a bulk edit needs no wire change of its own.

**Only the tab that pressed Start follows the game.** The event stream REPLAYS its whole log to every new
subscriber (that is what makes a reconnect lossless), so a lobby opened while a game is running hears the old
`episode_started` as if it had just happened. Navigating on it would bounce that tab straight to `/play` and
put the lobby — and its "End the session" button — out of reach for as long as the game lasts. So the redirect is
gated on :js:data:`startedHere`, set by this page's own Start click; every other tab stays on the lobby and shows
the running banner (`lobby_page._running_banner`, rendered on every load and unhidden by `paint`) with its
link to the live page.

**Validation here is a courtesy.** `validate` mirrors the server's two rules so Start is disabled before it is
clicked rather than after — the click that costs money should not be the thing that discovers the budget cap is
missing. The server checks again and is the one that refuses.

Owned by lane C.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `JS_LOBBY` |  |  |
| `JS_LOBBY_PAGE` |  |  |
