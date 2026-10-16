from __future__ import annotations

import math
import os
import re
import signal
import subprocess
import time
import uuid
from pathlib import Path
from typing import Protocol

from .agents import (
    AgentRunner,
    OmniRushSubprocessRunner,
    build_repair_prompt,
    validate_response,
)
from .artifacts import materialize
from .models import (
    AgentRequest,
    AgentRole,
    CommandResult,
    FailureClassification,
    FailureInfo,
    Profile,
    ProgressCallback,
    ProgressEvent,
    RepairOutcome,
    VerificationResult,
    VerificationStage,
)


DEFAULT_DOCKER_TIMEOUT = 300.0
MAX_REPAIR_ATTEMPTS = 5
_IMAGE_TAG = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,127}$")
_DEPENDENCY_OUTPUT = re.compile(
    r"(?i)(pip install|pip3 install|npm (?:ci|install)|pnpm install|yarn install|"
    r"(?:npm|pnpm|yarn)\s+(?:err!|error)|"
    r"could not find a version|no matching distribution|unable to resolve dependency|"
    r"err!.*(?:eresolve|dependency)|package .* not found|failed to fetch)"
)


class DockerRunner(Protocol):
    """Injectable boundary for Docker build and test commands."""

    def build(self, root: Path, image_tag: str, timeout: float) -> CommandResult:
        ...

    def test(self, image_tag: str, timeout: float) -> CommandResult:
        ...


def _decode(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


class DockerSubprocessRunner:
    """Run Docker commands in their own process groups with bounded lifetimes."""

    def __init__(self, binary: str | None = None):
        self.binary = binary or os.environ.get("DOCKER_BIN") or "docker"

    def build(self, root: Path, image_tag: str, timeout: float) -> CommandResult:
        return self._run((self.binary, "build", "-t", image_tag, "."), root, timeout)

    def test(self, image_tag: str, timeout: float) -> CommandResult:
        return self._run(
            (self.binary, "run", "--rm", image_tag, "make", "test"),
            None,
            timeout,
        )

    def run(
        self,
        command: tuple[str, ...],
        cwd: Path | None = None,
        timeout: float = DEFAULT_DOCKER_TIMEOUT,
    ) -> CommandResult:
        """Execute one already-assembled Docker command for test doubles."""

        return self._run(tuple(command), cwd, timeout)

    # These aliases make the adapter convenient for callers that name the
    # operation after the command while keeping the protocol small.
    run_build = build
    run_test = test

    def _run(
        self,
        command: tuple[str, ...],
        cwd: Path | None,
        timeout: float,
    ) -> CommandResult:
        _validate_timeout(timeout)
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                close_fds=True,
            )
        except OSError as exc:
            return CommandResult(
                command=command,
                returncode=127,
                stderr=str(exc),
                duration=time.monotonic() - started,
            )

        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._terminate(process)
            try:
                stdout, stderr = process.communicate(timeout=1.0)
            except subprocess.TimeoutExpired:
                # The process group should already be gone. This final fallback
                # still reaps the direct child if an unusual runtime ignores it.
                process.kill()
                stdout, stderr = process.communicate()
        return CommandResult(
            command=command,
            returncode=process.returncode,
            stdout=_decode(stdout),
            stderr=_decode(stderr),
            timed_out=timed_out,
            duration=time.monotonic() - started,
        )

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        """Terminate and reap a process group, escalating once if needed."""

        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                try:
                    process.terminate()
                except OSError:
                    pass
        try:
            process.wait(timeout=0.5)
            return
        except subprocess.TimeoutExpired:
            pass

        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            try:
                process.kill()
            except OSError:
                pass
        process.wait()


# Both spellings are useful at an injectable boundary and point to one implementation.
SubprocessDockerRunner = DockerSubprocessRunner
DockerCommandRunner = DockerSubprocessRunner


def _validate_timeout(timeout: float) -> None:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Docker timeout must be greater than zero")


def image_tag(value: str | None = None) -> str:
    """Return or validate a local-only Docker image tag."""

    tag = value or f"repro-doctor-target-{uuid.uuid4().hex}"
    if not _IMAGE_TAG.fullmatch(tag):
        raise ValueError(f"unsafe Docker image tag: {tag}")
    return tag


def classify_failure(stage: VerificationStage, result: CommandResult) -> FailureClassification:
    """Classify a command locally without a verifier agent."""

    if result.timed_out:
        return "timeout"
    if stage == "build":
        return "dependency" if _DEPENDENCY_OUTPUT.search(result.output) else "build"
    return "test"


def repair_role_for(failure: FailureInfo) -> AgentRole:
    """Select the only writer role allowed to repair a verification stage."""

    return "dockerfile-writer" if failure.stage == "build" else "test-script-writer"


def _failure(stage: VerificationStage, result: CommandResult) -> FailureInfo:
    return FailureInfo(
        stage=stage,
        classification=classify_failure(stage, result),
        command=result.command,
        output=result.output,
        timed_out=result.timed_out,
    )


def _error_result(command: tuple[str, ...], error: Exception) -> CommandResult:
    timed_out = isinstance(error, (TimeoutError, subprocess.TimeoutExpired))
    return CommandResult(
        command=command,
        returncode=None,
        stderr=str(error) or error.__class__.__name__,
        timed_out=timed_out,
    )


def _run_build(
    runner: DockerRunner,
    root: Path,
    tag: str,
    timeout: float,
) -> CommandResult:
    command = ("docker", "build", "-t", tag, ".")
    try:
        method = getattr(runner, "build", None) or getattr(runner, "run_build", None)
        if method is not None:
            result = method(root, tag, timeout)
        else:
            run = getattr(runner, "run", None)
            if run is None:
                raise AttributeError("Docker runner has no build method")
            result = run(command, root, timeout)
    except Exception as exc:
        return _error_result(command, exc)
    if not isinstance(result, CommandResult):
        return _error_result(command, TypeError("Docker build runner returned an invalid result"))
    return result


def _run_test(runner: DockerRunner, tag: str, timeout: float) -> CommandResult:
    command = ("docker", "run", "--rm", tag, "make", "test")
    try:
        method = getattr(runner, "test", None) or getattr(runner, "run_test", None)
        if method is not None:
            result = method(tag, timeout)
        else:
            run = getattr(runner, "run", None)
            if run is None:
                raise AttributeError("Docker runner has no test method")
            result = run(command, None, timeout)
    except Exception as exc:
        return _error_result(command, exc)
    if not isinstance(result, CommandResult):
        return _error_result(command, TypeError("Docker test runner returned an invalid result"))
    return result


def verify_snapshot(
    root: Path,
    *,
    docker_runner: DockerRunner | None = None,
    timeout: float = DEFAULT_DOCKER_TIMEOUT,
    tag: str | None = None,
) -> VerificationResult:
    """Build the materialized snapshot and run its generated test target."""

    _validate_timeout(timeout)
    image = image_tag(tag)
    runner = docker_runner or DockerSubprocessRunner()
    build_result = _run_build(runner, root, image, timeout)
    if not build_result.succeeded:
        return VerificationResult(
            status="failed",
            image_tag=image,
            build_result=build_result,
            failure=_failure("build", build_result),
        )

    test_result = _run_test(runner, image, timeout)
    if not test_result.succeeded:
        return VerificationResult(
            status="failed",
            image_tag=image,
            build_result=build_result,
            test_result=test_result,
            failure=_failure("test", test_result),
        )
    return VerificationResult(
        status="passed",
        image_tag=image,
        build_result=build_result,
        test_result=test_result,
    )


def _repair_detail(error: Exception) -> str:
    return str(error) or error.__class__.__name__


def _emit_repair_start(
    progress: ProgressCallback | None,
    role: AgentRole,
    attempt: int,
) -> None:
    if progress is None:
        return
    try:
        progress(ProgressEvent(role, "start", f"repair attempt {attempt}"))
    except Exception:
        return


def verify_and_repair(
    root: Path,
    profile: Profile,
    *,
    docker_runner: DockerRunner | None = None,
    repair_runner: AgentRunner | None = None,
    docker_timeout: float = DEFAULT_DOCKER_TIMEOUT,
    repair_timeout: float,
    progress: ProgressCallback | None = None,
    tag: str | None = None,
) -> VerificationResult:
    """Verify once and make no more than five focused writer repairs."""

    _validate_timeout(docker_timeout)
    _validate_timeout(repair_timeout)
    image = image_tag(tag)
    selected_repair_runner = repair_runner or OmniRushSubprocessRunner()
    current = verify_snapshot(
        root,
        docker_runner=docker_runner,
        timeout=docker_timeout,
        tag=image,
    )
    repairs: list[RepairOutcome] = []

    while not current.passed and len(repairs) < MAX_REPAIR_ATTEMPTS:
        assert current.failure is not None
        failure = current.failure
        role = repair_role_for(failure)
        attempt = len(repairs) + 1
        request = AgentRequest(
            role=role,
            root=root,
            profile=profile,
            prompt=build_repair_prompt(
                role,
                root,
                profile,
                stage=failure.stage,
                classification=failure.classification,
                output=failure.output,
                attempt=attempt,
            ),
            timeout=repair_timeout,
        )
        try:
            _emit_repair_start(progress, role, attempt)
            response = validate_response(
                selected_repair_runner.run(request, progress),
                role,
            )
            materialize(root, response.artifacts)
            outcome = RepairOutcome(
                attempt=attempt,
                role=role,
                classification=failure.classification,
                success=True,
                changed_files=tuple(artifact.path for artifact in response.artifacts),
                detail="validated repair materialized",
                stage=failure.stage,
                failure_output=failure.output,
                failed_command=failure.command,
            )
        except Exception as exc:
            outcome = RepairOutcome(
                attempt=attempt,
                role=role,
                classification=failure.classification,
                success=False,
                detail=_repair_detail(exc),
                stage=failure.stage,
                failure_output=failure.output,
                failed_command=failure.command,
            )
        repairs.append(outcome)
        current = verify_snapshot(
            root,
            docker_runner=docker_runner,
            timeout=docker_timeout,
            tag=image,
        )

    return VerificationResult(
        status=current.status,
        image_tag=current.image_tag,
        build_result=current.build_result,
        test_result=current.test_result,
        failure=current.failure,
        retry_count=len(repairs),
        repairs=tuple(repairs),
    )
