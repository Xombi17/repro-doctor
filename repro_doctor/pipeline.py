from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

from .agents import AgentRunner, DEFAULT_AGENT_TIMEOUT, InProcessAgentRunner
from .artifacts import generate_artifacts, materialize
from .detect import detect_repository
from .inputs import CloneRunner, copy_snapshot, ensure_output_is_safe, isolated_snapshot
from .models import Artifact, Profile, ProgressCallback, RunResult
from .orchestration import orchestrate_generation
from .patching import build_patch, write_patch
from .report import render_report
from .verifier import (
    DEFAULT_DOCKER_TIMEOUT,
    DockerRunner,
    verify_and_repair,
)


class GenerationRunner(Protocol):
    """Boundary for the in-process generator and future agent runners."""

    def generate(self, root: Path, profile: Profile) -> tuple[Artifact, ...]:
        ...


class InProcessGenerationRunner:
    def generate(self, root: Path, profile: Profile) -> tuple[Artifact, ...]:
        return generate_artifacts(root, profile)


def process_repository(
    source: str,
    output_dir: Path,
    *,
    generation_runner: GenerationRunner | None = None,
    agent_runner: AgentRunner | None = None,
    mode: Literal["local", "agent"] = "local",
    agent_timeout: float = DEFAULT_AGENT_TIMEOUT,
    progress: ProgressCallback | None = None,
    clone_runner: CloneRunner | None = None,
    verify: bool = False,
    docker_runner: DockerRunner | None = None,
    repair_runner: AgentRunner | None = None,
    docker_timeout: float = DEFAULT_DOCKER_TIMEOUT,
) -> RunResult:
    """Analyze an isolated snapshot and write a patch plus report.

    Direct callers retain the deterministic ``local`` default. The CLI exposes
    both modes and defaults to ``agent`` for the user-facing workflow.
    """

    if mode not in {"local", "agent"}:
        raise ValueError("mode must be 'local' or 'agent'")

    ensure_output_is_safe(source, output_dir)
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = generation_runner or InProcessGenerationRunner()
    verification = None

    with isolated_snapshot(source, clone_runner=clone_runner) as snapshot:
        baseline = snapshot.root.parent / "baseline"
        copy_snapshot(snapshot.root, baseline)
        profile = detect_repository(snapshot.root)
        if mode == "local":
            artifacts = runner.generate(snapshot.root, profile)
        else:
            artifacts = orchestrate_generation(
                snapshot.root,
                profile,
                runner=agent_runner,
                timeout=agent_timeout,
                progress=progress,
            )
        materialize(snapshot.root, artifacts)
        if verify:
            selected_repair_runner = repair_runner or agent_runner
            if selected_repair_runner is None and mode == "local":
                selected_repair_runner = InProcessAgentRunner()
            verification = verify_and_repair(
                snapshot.root,
                profile,
                docker_runner=docker_runner,
                repair_runner=selected_repair_runner,
                docker_timeout=docker_timeout,
                repair_timeout=agent_timeout,
                progress=progress,
            )
        patch_result = build_patch(baseline, snapshot.root)

    patch_path = output_dir / "repro-doctor.patch"
    report_path = output_dir / "repro-doctor-report.md"
    write_patch(patch_path, patch_result)
    report_path.write_text(
        render_report(
            profile,
            patch_result.changed_files,
            retry_count=verification.retry_count if verification else 0,
            verification_result=verification.status if verification else "not run",
            verification=verification,
        ),
        encoding="utf-8",
    )
    return RunResult(
        patch_path=patch_path,
        report_path=report_path,
        profile=profile,
        changed_files=patch_result.changed_files,
        retry_count=verification.retry_count if verification else 0,
        verification_result=verification.status if verification else "not run",
        verification=verification,
    )
