// interlens: a framework for scaffolding and interpreting multi-agent conversations
// Copyright (C) 2026 Siddharth M. Bhatia
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of version 3 of the GNU Affero General Public License
// as published by the Free Software Foundation.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// Vercel project configuration (executed at build time; same properties as vercel.json).
// Deliberately dependency-free: no `@vercel/config` import, so this Python repo needs no package.json —
// the package only provides optional types/route helpers, which we don't use.
//
// Docs are built with Zensical (see the mkdocs.yml header): gen_ref_pages.py writes the API stub pages,
// nav, and llms.txt files, then `zensical build` renders the static site into `site/`. uv drives the
// toolchain — it reads requires-python from pyproject.toml, provisions its own CPython, and installs only
// the `docs` dependency group (never the interlens package or torch: mkdocstrings/griffe reads src/
// statically). Every branch push gets a Vercel preview URL; pushes to main deploy production.

export const config = {
  // Plain static site rendered by Zensical — no framework preset.
  framework: null,

  // uv is available on Vercel's Python-aware build image; the curl fallback covers images without it
  // (the standalone installer lands in ~/.local/bin, hence the PATH export in buildCommand).
  installCommand: 'command -v uv || curl -LsSf https://astral.sh/uv/install.sh | sh',
  buildCommand:
    'export PATH="$HOME/.local/bin:$PATH" && uv run --only-group docs python docs/gen_ref_pages.py && uv run --only-group docs zensical build --clean --strict',

  // The site lives at docs.sidmb.com/interlens (site_url in mkdocs.yml — the single source of truth for
  // the published URL): mkdocs.yml sets `site_dir: site/interlens`, so serving `site/` at the domain root
  // puts every page under the /interlens/ subpath, leaving room for sibling doc sites on the same domain.
  outputDirectory: 'site',
  redirects: [{ source: '/', destination: '/interlens/', permanent: false }],

  // Skip deployments for pushes that can't affect the rendered docs (mirrors the paths filter the old
  // GitHub Pages workflow used). Exit 0 = skip the build, exit 1 = build.
  ignoreCommand: 'git diff --quiet HEAD^ HEAD -- docs src mkdocs.yml README.md pyproject.toml uv.lock vercel.ts',
};
