"""Command-line interface for ProjectLens."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from projectlens.analysis.models import AnalysisOptions
from projectlens.analysis.pipeline import analyze
from projectlens.analysis.scanner import ScanError
from projectlens.report import format_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="projectlens", description="Analyze a local software repository.")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze_command = commands.add_parser("analyze", help="Analyze a repository.")
    analyze_command.add_argument("path", help="Path to the repository to analyze.")
    analyze_command.add_argument("--output", metavar="FILE", help="Write the analysis JSON to FILE.")
    analyze_command.add_argument("--top", type=_non_negative_int, default=10, metavar="N", help="Largest files to show (default: 10).")
    analyze_command.add_argument("--max-diagnostics", type=_non_negative_int, default=5, metavar="N", help="Diagnostics to show in the summary (default: 5).")
    analyze_command.add_argument("--git-history", action="store_true", help="Include bounded Git history churn metrics.")
    analyze_command.add_argument("--history-days", type=_history_days, default=180, metavar="N", help="Git history window in days (1-3650; default: 180).")
    return parser


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return number


def _history_days(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer from 1 to 3650") from exc
    if not 1 <= number <= 3650:
        raise argparse.ArgumentTypeError("must be an integer from 1 to 3650")
    return number


def _print_safe(text: str, *, file=None) -> None:
    stream = file or sys.stdout
    encoding = getattr(stream, "encoding", None) or "utf-8"
    safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    print(safe_text, file=stream)


def _write_json(path_text: str, content: str) -> None:
    destination = Path(path_text)
    parent = destination.parent if str(destination.parent) else Path(".")
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            stream.write(content)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "analyze":
        return 2
    root = Path(args.path)
    excluded_paths: tuple[str, ...] = ()
    if args.output:
        output_path = Path(args.output)
        try:
            excluded_paths = (str(output_path.resolve(strict=False)),)
        except (OSError, ValueError, RuntimeError) as exc:
            _print_safe(f"error: invalid output path: {exc}", file=sys.stderr)
            return 1
    try:
        result = analyze(AnalysisOptions(str(root), excluded_paths=excluded_paths, git_history=args.git_history, history_days=args.history_days), largest_limit=args.top)
    except (ScanError, OSError, ValueError) as exc:
        _print_safe(f"error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        try:
            _write_json(args.output, result.to_json())
        except (OSError, ValueError, RuntimeError) as exc:
            _print_safe(f"error: could not write JSON output {args.output!r}: {exc}", file=sys.stderr)
            return 1

    _print_safe(format_summary(result, str(root), max_diagnostics=args.max_diagnostics))
    return 3 if result.partial else 0
