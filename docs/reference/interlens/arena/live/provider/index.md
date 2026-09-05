# `interlens.arena.live.provider`

The seam between the live server and whatever experiment supplies its games.

The server knows how to run a negotiation live — stream it, block a seat on a browser, swap an occupant — and
knows NOTHING about instance banks, framings, scaffolds, oracle stacks or which models an experiment can afford
to call. All of that enters through :class:`ScenarioProvider`, which the experiment implements (for the rational
agents work, `experiments/rational_agents/live_play.py` implements it over `run.py`'s existing assembly
helpers).

That direction of dependency is the whole design: an experiment's scenario assembly is intricate, versioned and
changes with the research, and copying any of it into the library would create a second copy that goes stale.
The provider hands over already-assembled objects, so interlens never learns what a "framing" is.

Nothing here does any work. These are the shapes the four implementation lanes agree on.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `SEAT_KINDS` |  |  |
| `THINKING_PREFERENCE` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`BankInfo`](BankInfo.md) | One instance bank the lobby may draw a game from. |
| [`ModelInfo`](ModelInfo.md) | One model the lobby may offer for an `llm` seat. |
| [`PreparedGame`](PreparedGame.md) | One playable game, fully assembled — the provider's answer to a lobby configuration. |
| [`ScenarioProvider`](ScenarioProvider.md) | What an experiment must supply for its games to be playable live. |
| [`SeatConfig`](SeatConfig.md) | What the lobby says should sit in one seat — the unit of both initial configuration and a mid-game swap. |

## Functions

| Name | Summary |
|---|---|
| [`default_model_id`](default_model_id.md) | Which model a seat that has just become an `llm` seat is pre-selected to. |
| [`default_thinking`](default_thinking.md) | The thinking mode a seat on this model starts in: the first of :data:`THINKING_PREFERENCE` the model accepts, falling back to its first declared mode if it accepts none of them (a provider free to invent mode names must still get a mode that model can take). |
