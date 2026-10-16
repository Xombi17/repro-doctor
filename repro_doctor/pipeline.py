from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .artifacts import generate_artifacts, materialize
from .detect import detect_python
from .inputs import CloneRunner, copy_snapshot, ensure_output_is_safe, isolated_snapshot
from .models import Artifact, PythonProfile, RunResult
from .patching import build_patch, write_patch
from .report import render_report


class GenerationRunner(Protocol):
    """Boundary for the in-process generator and future agent runners."""

    def generate(self, root: Path, profile: PythonProfile) -> tuple[Artifact, ...]:
        ...


class InProcessGenerationRunner:
    def generate(self, root: Path, profile: PythonProfile) -> tuple[Artifact, ...]:
        return generate_artifacts(root, profile)


def process_repository(
    source: str,
    output_dir: Path,
    *,
    generation_runner: GenerationRunner | None = None,
    clone_runner: CloneRunner | None = None,
) -> RunResult:
    """Analyze an isolated snapshot and write a patch plus report."""

    ensure_output_is_safe(source, output_dir)
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = generation_runner or InProcessGenerationRunner()

    with isolated_snapshot(source, clone_runner=clone_runner) as snapshot:
        baseline = snapshot.root.parent / "baseline"
        copy_snapshot(snapshot.root, baseline)
        profile = detect_python(snapshot.root)
        artifacts = runner.generate(snapshot.root, profile)
        materialize(snapshot.root, artifacts)
        patch_result = build_patch(baseline, snapshot.root)

    patch_path = output_dir / "repro-doctor.patch"
    report_path = output_dir / "repro-doctor-report.md"
    write_patch(patch_path, patch_result)
    report_path.write_text(
        render_report(profile, patch_result.changed_files),
        encoding="utf-8",
    )
    return RunResult(
        patch_path=patch_path,
        report_path=report_path,
        profile=profile,
        changed_files=patch_result.changed_files,
    )
