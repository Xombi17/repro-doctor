from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Snapshot:
    """An isolated, disposable repository snapshot."""

    root: Path
    source: str
    kind: Literal["local", "github"]


@dataclass(frozen=True)
class PythonProfile:
    """Structured Python repository data shared by artifact writers."""

    stack: Literal["python"]
    runtime: str
    runtime_source: str
    dependency_files: tuple[str, ...]
    lockfile: str | None
    test_command: str
    package_name: str | None
    confidence: Literal["high", "medium"]
    signals: tuple[str, ...]


@dataclass(frozen=True)
class Artifact:
    """A text file to materialize in an isolated snapshot."""

    path: str
    content: str
    reason: str


@dataclass(frozen=True)
class PatchResult:
    patch: bytes
    changed_files: tuple[str, ...]


@dataclass(frozen=True)
class RunResult:
    patch_path: Path
    report_path: Path
    profile: PythonProfile
    changed_files: tuple[str, ...]
    retry_count: int = 0
    verification_result: str = "not run"
