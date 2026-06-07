"""CLI entry point for diagram-sanitizer."""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and run the sanitizer."""
    parser = argparse.ArgumentParser(
        description="Validate and auto-correct ASCII diagrams for structural integrity."
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to a file containing the diagram (reads from stdin if omitted).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the full JSON report instead of the corrected diagram.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"diagram-sanitizer {__import__('diagram_sanitizer').__version__}",
    )

    args = parser.parse_args(argv)

    if args.file:
        with open(args.file) as f:
            diagram = f.read()
    else:
        diagram = sys.stdin.read()

    # TODO: integrate the actual sanitizer logic
    print(diagram)

    return 0


if __name__ == "__main__":
    sys.exit(main())
