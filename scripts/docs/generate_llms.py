"""Generate the LLM-friendly source assets that were previously emitted by ``mkdocs-llmstxt``.

Zensical does not currently provide an equivalent to that MkDocs plugin. This pre-build step writes a concise ``llms.txt`` link index and a combined ``llms-full.txt`` document into the docs directory so Zensical copies them in both preview and production modes.
"""

from pathlib import Path


ROOT = Path(__file__).parents[2]
DOCS_ROOT = ROOT / "docs"
SITE_URL = "https://sid-mb.github.io/interlens"
DESCRIPTION = "interlens is a harness for multi-agent conversations with first-class interpretability, including activation capture, steering, activation patching, and token logprobs."


def title_for(markdown_path: Path) -> str:
	"""Extract the first Markdown heading from a documentation page.

	Args:
		markdown_path: Markdown source file whose display title is needed.

	Returns:
		The first ATX heading without its marker, falling back to the filename stem when no heading exists.
	"""
	for line in markdown_path.read_text(encoding="utf-8").splitlines():
		if line.startswith("# "):
			return line.removeprefix("# ").strip()
	return markdown_path.stem.replace("_", " ").title()


def generate_llms_files(output_root: Path = DOCS_ROOT) -> None:
	"""Write ``llms.txt`` and ``llms-full.txt`` as Zensical source assets.

	Args:
		output_root: Directory that receives both generated text files; defaults to the documentation source directory.

	Implementation:
		The compact index links the overview and ordered example pages. The full document uses ``README.md`` as the overview because ``docs/index.md`` deliberately contains only a snippets directive pointing to that single source of truth. Writing into ``docs`` lets Zensical copy the files during both ``serve`` and ``build``.
	"""
	output_root.mkdir(parents=True, exist_ok=True)
	examples = sorted((DOCS_ROOT / "examples").glob("*.md"), key=lambda path: (path.name != "README.md", path.name))
	index_lines = ["# interlens", "", f"> {DESCRIPTION}", "", "## Overview", "", f"- [interlens]({SITE_URL}/)", "", "## Examples (simple to advanced)", ""]
	index_lines.extend(f"- [{title_for(path)}]({SITE_URL}/examples/{'' if path.name == 'README.md' else path.stem + '/'})" for path in examples)
	(output_root / "llms.txt").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

	sections = [("Overview", ROOT / "README.md"), *(("Example", path) for path in examples)]
	full_parts = ["# interlens", "", f"> {DESCRIPTION}"]
	for label, path in sections:
		full_parts.extend(("", f"## {label}: {title_for(path)}", "", path.read_text(encoding="utf-8").strip()))
	(output_root / "llms-full.txt").write_text("\n".join(full_parts) + "\n", encoding="utf-8")


def main() -> None:
	"""Generate both LLM-friendly source assets and report their destination."""
	generate_llms_files()
	print(f"Generated llms.txt and llms-full.txt in {DOCS_ROOT.relative_to(ROOT)}")


if __name__ == "__main__":
	main()
