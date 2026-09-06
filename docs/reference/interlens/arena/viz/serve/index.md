# `serve`

Module `interlens.arena.viz.serve`

Hand the rendered pages to a browser over HTTP, for when the filesystem the pages live on is not the one the
browser runs on.

The pages themselves need no server — they are self-contained and open by double-click. This exists for the
usual research setup: you are ssh'd into a cluster node, the run directory is there, and your browser is on your
laptop. Rather than copying a directory of HTML back, serve it in place and forward one port.

Stdlib only (:mod:`http.server`), so this adds no dependency to a package whose visualizer is otherwise pure
string-building. The server is threading so a page's several asset-free requests do not serialize, and it is
read-only by construction: :class:`~http.server.SimpleHTTPRequestHandler` implements GET/HEAD and nothing else.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `DEFAULT_HOST` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`make_server`](make_server.md) | Bind (but do not run) an HTTP server rooted at `directory`. |
| [`serve_banner`](serve_banner.md) | The startup message: where the pages are, the URL to open, and — because the reader is usually on a cluster node with no browser — the exact `ssh -L` command to forward `port` to their laptop, with this machine's real hostname already filled in. |
| [`serve_directory`](serve_directory.md) | Serve `directory` over HTTP until interrupted — bind, print :func:`serve_banner`, then block in `serve_forever`. |
