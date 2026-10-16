from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__
from .errors import ReproDoctorError
from .pipeline import process_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repro-doctor",
        description="Generate an applyable reproducibility patch for a Python or Node.js repository.",
    )
    parser.add_argument("source", help="local repository path or GitHub HTTPS URL")
    parser.add_argument(
        "--output-dir",
        default="repro-doctor-output",
        type=Path,
        help="directory for the patch and Markdown report (default: %(default)s)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = process_repository(args.source, args.output_dir)
    except ReproDoctorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: filesystem operation failed: {exc}", file=sys.stderr)
        return 2

    if getattr(result.profile, "stack", "") == "node":
        stack = "Node.js/TypeScript" if getattr(result.profile, "typescript", False) else "Node.js"
    else:
        stack = "Python"
    print(f"Detected {stack} repository ({result.profile.confidence} confidence)")
    print(f"Patch: {result.patch_path}")
    print(f"Report: {result.report_path}")
    print(f"Changed files: {len(result.changed_files)}")
    return 0
