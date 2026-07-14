"""Orchestrate generated documentation inputs and Zensical commands.

This wrapper is the single local and CI entrypoint for documentation. It regenerates the module reference tree and LLM-friendly source assets before every preview or build, then delegates rendering to Zensical.
"""

import argparse
import subprocess
from collections.abc import Sequence

from generate_llms import generate_llms_files
from generate_reference import generate_reference


def run(command: str, zensical_args: Sequence[str] = ()) -> None:
	"""Generate documentation inputs and run a Zensical command.

	Args:
		command: Either ``serve`` for a watched local preview or ``build`` for production output.
		zensical_args: Additional command-line arguments forwarded to Zensical.

	Raises:
		subprocess.CalledProcessError: If Zensical exits unsuccessfully.

	Implementation:
		Production builds always use ``--clean`` to prevent stale generated output. Both modes generate the LLM text files before Zensical starts so the files are available from the preview server and production site alike.
	"""
	count = generate_reference()
	print(f"Generated {count} API reference pages", flush=True)
	generate_llms_files()
	print("Generated llms.txt and llms-full.txt", flush=True)
	arguments = ["zensical", command]
	if command == "build":
		arguments.append("--clean")
	arguments.extend(zensical_args)
	subprocess.run(arguments, check=True)


def main() -> None:
	"""Parse the wrapper command and forward remaining arguments to Zensical.

	Implementation:
		A preview interrupted with ``Ctrl+C`` exits with the conventional status code 130 without printing a Python wrapper traceback.
	"""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("command", choices=("serve", "build"), help="Zensical command to run")
	parser.add_argument("zensical_args", nargs=argparse.REMAINDER, help="additional arguments passed to Zensical")
	args = parser.parse_args()
	try:
		run(args.command, args.zensical_args)
	except KeyboardInterrupt:
		raise SystemExit(130) from None


if __name__ == "__main__":
	main()
