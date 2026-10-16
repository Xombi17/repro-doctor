from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__
from .agents import DEFAULT_AGENT_TIMEOUT
from .errors import ReproDoctorError
from .models import ProgressEvent
from .pipeline import process_repository
from .verifier import DEFAULT_DOCKER_TIMEOUT


def build_parser() -> argparse.ArgumentParser:
    parser_options = {
        "prog": "repro-doctor",
        "description": "Generate an applyable reproducibility patch for a Python or Node.js repository.",
    }
    # Python 3.14 adds colored argparse help by default. Keep the CLI contract
    # stable for scripts and tests, while retaining compatibility with 3.12.
    try:
        parser = argparse.ArgumentParser(color=False, **parser_options)
    except TypeError:
        parser = argparse.ArgumentParser(**parser_options)
    parser.add_argument("source", help="local repository path or GitHub HTTPS URL")
    parser.add_argument(
        "--output-dir",
        default="repro-doctor-output",
        type=Path,
        help="directory for the patch and Markdown report (default: %(default)s)",
    )
    parser.add_argument(
        "--mode",
        choices=("agent", "local"),
        default="agent",
        help=(
            "generation mode: agent runs four parallel OmniRush roles; local uses "
            "the deterministic in-process generator (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--agent-timeout",
        type=float,
        default=DEFAULT_AGENT_TIMEOUT,
        help="maximum seconds allowed for each agent role (default: %(default)s)",
    )
    parser.add_argument(
        "--docker-timeout",
        type=float,
        default=DEFAULT_DOCKER_TIMEOUT,
        help="maximum seconds allowed for each Docker command (default: %(default)s)",
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="skip Docker verification for offline local development",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def _render_progress(event: ProgressEvent) -> None:
    print(f"[{event.role}] {event.kind}: {event.detail}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = process_repository(
            args.source,
            args.output_dir,
            mode=args.mode,
            agent_timeout=args.agent_timeout,
            docker_timeout=args.docker_timeout,
            verify=not args.skip_verification,
            progress=_render_progress if args.mode == "agent" else None,
        )
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
    if result.verification is not None:
        print(f"Verification: {result.verification.status}")
        print(f"Verification retries: {result.verification.retry_count}")
        if not result.verification.passed:
            failure = result.verification.failure
            if failure is not None:
                print(
                    f"Verification failure: {failure.stage}/{failure.classification}",
                    file=sys.stderr,
                )
            return 1
    return 0
