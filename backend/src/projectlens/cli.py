"""Command-line interface for ProjectLens."""

import argparse
import sys
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="projectlens", description="Analyze a local software repository.")
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="Analyze a repository (not implemented yet).")
    analyze.add_argument("path", help="Path to the repository to analyze.")
    analyze.add_argument("--output", metavar="FILE", help="Write the analysis JSON to FILE.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "analyze":
        print("ProjectLens analysis is not implemented yet.", file=sys.stderr)
        return 1
    return 0
