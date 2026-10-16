from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import threading
from dataclasses import asdict
from typing import Mapping, Protocol, cast

from .artifacts import generate_artifacts
from .errors import (
    AgentProcessError,
    AgentProtocolError,
    AgentTimeoutError,
    ArtifactValidationError,
)
from .models import (
    AgentEventKind,
    AgentRequest,
    AgentResponse,
    AgentRole,
    Artifact,
    NodeProfile,
    Profile,
    ProgressCallback,
    ProgressEvent,
    PythonProfile,
)


AGENT_ROLES: tuple[AgentRole, ...] = (
    "stack-detector",
    "dockerfile-writer",
    "test-script-writer",
    "readme-writer",
)
DEFAULT_AGENT_TIMEOUT = 120.0

_ROLE_ALLOWLIST: dict[AgentRole, frozenset[str]] = {
    "stack-detector": frozenset(),
    "dockerfile-writer": frozenset({"Dockerfile"}),
    "test-script-writer": frozenset(
        {
            "Makefile",
            ".nvmrc",
            ".python-version",
            "runtime.txt",
            "requirements.repro-doctor.txt",
            "dependencies.repro-doctor.md",
        }
    ),
    "readme-writer": frozenset({"README.repro-doctor.md"}),
}

_PROFILE_FIELDS: dict[str, frozenset[str]] = {
    "python": frozenset(
        {
            "stack",
            "runtime",
            "runtime_source",
            "dependency_files",
            "lockfile",
            "test_command",
            "package_name",
            "confidence",
            "signals",
        }
    ),
    "node": frozenset(
        {
            "stack",
            "runtime",
            "runtime_source",
            "dependency_files",
            "lockfile",
            "package_manager",
            "package_manager_source",
            "package_manager_spec",
            "test_command",
            "test_script",
            "package_name",
            "typescript",
            "test_files",
            "confidence",
            "signals",
        }
    ),
}

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b([A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL|AUTH)[A-Z0-9_]*)\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s]+)"
)
_SECRET_FLAG = re.compile(
    r"(?i)(--?(?:api[-_]?key|token|secret|password|credential))\s+[^\s]+"
)


class AgentRunner(Protocol):
    """Replaceable boundary for real, fake, and in-process agent runners."""

    def run(
        self,
        request: AgentRequest,
        progress: ProgressCallback | None = None,
    ) -> AgentResponse:
        ...


def _emit(
    progress: ProgressCallback | None,
    role: AgentRole,
    kind: str,
    detail: str,
) -> None:
    if progress is None:
        return
    event = ProgressEvent(role, cast(AgentEventKind, kind), detail)
    try:
        progress(event)
    except Exception:
        # Progress output must not turn a successful generation into a failed run.
        return


def _safe_text(value: str) -> str:
    value = _SECRET_ASSIGNMENT.sub(r"\1=<redacted>", value)
    return _SECRET_FLAG.sub(r"\1 <redacted>", value)


def _safe_profile_payload(profile: Profile) -> dict[str, object]:
    payload = asdict(profile)
    for key, value in tuple(payload.items()):
        if isinstance(value, str):
            payload[key] = _safe_text(value)
        elif isinstance(value, list):
            payload[key] = [
                _safe_text(item) if isinstance(item, str) else item for item in value
            ]
    return payload


def _planned_paths(root: Path, profile: Profile) -> tuple[str, ...]:
    return tuple(artifact.path for artifact in generate_artifacts(root, profile))


def build_role_prompt(role: AgentRole, root: Path, profile: Profile) -> str:
    """Build a self-contained, metadata-only prompt for one role."""

    profile_json = json.dumps(
        _safe_profile_payload(profile),
        ensure_ascii=True,
        sort_keys=True,
    )
    planned_paths = _planned_paths(root, profile)
    planned = ", ".join(f"`{path}`" for path in planned_paths) or "none"
    assigned = ", ".join(
        f"`{path}`" for path in planned_paths if path in _ROLE_ALLOWLIST[role]
    ) or "none"
    base = f"""You are the {role} role in repro-doctor.

Work read-only in the current repository directory. Do not create, edit, delete,
or rename files. Do not run commands that mutate the repository. Return exactly
one JSON object and no prose. Do not include environment values, credentials,
tokens, or other secrets in the response.

The deterministic local profile is the safety baseline:
{profile_json}

The controller's deterministic artifact plan is: {planned}
The paths assigned to this role are: {assigned}. Return every assigned path;
return an empty artifacts array only when this role has no assigned paths because
the source already provides its files.
"""
    if role == "stack-detector":
        return base + """
Inspect repository metadata and return an advisory profile using the same field
names and value types as the supplied profile. Do not return an artifacts field.
The controller validates this profile and continues to use the deterministic
profile for materialization.

JSON shape:
{"role":"stack-detector","profile":{...}}
"""
    if role == "dockerfile-writer":
        return base + """
Return the assigned Dockerfile artifact when it is in the deterministic plan.
The only allowed artifact path is Dockerfile. Preserve the detected runtime,
package manager, usable lockfiles, and test entry point.

JSON shape:
{"role":"dockerfile-writer","artifacts":[{"path":"Dockerfile","content":"...","reason":"..."}]}
"""
    if role == "test-script-writer":
        return base + """
Add or repair the test entry point and return every assigned artifact. The
allowed artifact paths are Makefile and, only when requested by the deterministic
plan, .nvmrc, .python-version, runtime.txt, requirements.repro-doctor.txt, or
dependencies.repro-doctor.md. Do not change application source files.

JSON shape:
{"role":"test-script-writer","artifacts":[{"path":"Makefile","content":"...","reason":"..."}]}
"""
    return base + """
Write the assigned reproducibility documentation artifact. The only allowed
artifact path is README.repro-doctor.md. Include setup, run, test, and Docker
usage and describe the generated files without including secrets.

JSON shape:
{"role":"readme-writer","artifacts":[{"path":"README.repro-doctor.md","content":"...","reason":"..."}]}
"""


def build_repair_prompt(
    role: AgentRole,
    root: Path,
    profile: Profile,
    *,
    stage: str,
    classification: str,
    output: str,
    attempt: int,
) -> str:
    """Build a focused writer request using the Phase 3 response contract."""

    if role not in {"dockerfile-writer", "test-script-writer"}:
        raise AgentProtocolError(f"{role} cannot repair verification failures")
    profile_json = json.dumps(
        _safe_profile_payload(profile),
        ensure_ascii=True,
        sort_keys=True,
    )
    allowed = ", ".join(f"`{path}`" for path in sorted(_ROLE_ALLOWLIST[role]))
    safe_output = _safe_text(output)
    return f"""You are the {role} role in repro-doctor repair attempt {attempt}.

Work read-only in the current repository directory. Return exactly one JSON object
and no prose. Do not edit application source files, run mutating repository
commands, or return files outside your assigned scope: {allowed}.

The deterministic local profile is:
{profile_json}

The isolated snapshot failed Docker verification at stage `{stage}` with local
classification `{classification}`. Captured command output follows:
<verification-output>
{safe_output}
</verification-output>

Make the smallest reproducibility-only repair that addresses this failure.
Preserve the detected runtime, package manager, usable lockfiles, and test entry
point. A test failure is a test-entry-point or generated-environment issue; do
not repair application behavior. Return only artifacts that should be replaced.

Use the existing validated response shape:
{{"role":"{role}","artifacts":[{{"path":"...","content":"...","reason":"..."}}]}}
"""


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AgentProtocolError(f"{label} must be a JSON object")
    return value


def _require_exact_keys(
    value: Mapping[str, object],
    expected: frozenset[str],
    label: str,
) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = ", ".join(sorted(expected - actual)) or "none"
        extra = ", ".join(sorted(actual - expected)) or "none"
        raise AgentProtocolError(
            f"{label} has invalid fields (missing: {missing}; extra: {extra})"
        )


def _string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise AgentProtocolError(f"{label} must be a string")
    return value


def _optional_string(value: object, label: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise AgentProtocolError(f"{label} must be a string or null")
    return value


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) for item in value
    ):
        raise AgentProtocolError(f"{label} must be an array of strings")
    return tuple(value)


def validate_profile(value: object) -> Profile:
    """Validate and construct a profile returned by stack-detector."""

    data = _require_mapping(value, "profile")
    stack = _string(data.get("stack"), "profile.stack")
    if stack not in _PROFILE_FIELDS:
        raise AgentProtocolError(f"profile.stack has unsupported value: {stack}")
    _require_exact_keys(data, _PROFILE_FIELDS[stack], "profile")
    runtime = _string(data["runtime"], "profile.runtime")
    runtime_source = _string(data["runtime_source"], "profile.runtime_source")
    dependency_files = _string_tuple(data["dependency_files"], "profile.dependency_files")
    lockfile = _optional_string(data["lockfile"], "profile.lockfile")
    test_command = _string(data["test_command"], "profile.test_command")
    package_name = _optional_string(data["package_name"], "profile.package_name")
    confidence = _string(data["confidence"], "profile.confidence")
    if confidence not in {"high", "medium"}:
        raise AgentProtocolError(f"profile.confidence has unsupported value: {confidence}")
    signals = _string_tuple(data["signals"], "profile.signals")
    if stack == "python":
        return PythonProfile(
            stack="python",
            runtime=runtime,
            runtime_source=runtime_source,
            dependency_files=dependency_files,
            lockfile=lockfile,
            test_command=test_command,
            package_name=package_name,
            confidence=cast("PythonProfile.__annotations__['confidence']", confidence),
            signals=signals,
        )

    package_manager = _string(data["package_manager"], "profile.package_manager")
    if package_manager not in {"npm", "pnpm", "yarn"}:
        raise AgentProtocolError(
            f"profile.package_manager has unsupported value: {package_manager}"
        )
    package_manager_source = _string(
        data["package_manager_source"], "profile.package_manager_source"
    )
    package_manager_spec = _optional_string(
        data["package_manager_spec"], "profile.package_manager_spec"
    )
    test_script = _optional_string(data["test_script"], "profile.test_script")
    typescript = data["typescript"]
    if not isinstance(typescript, bool):
        raise AgentProtocolError("profile.typescript must be a boolean")
    test_files = _string_tuple(data["test_files"], "profile.test_files")
    return NodeProfile(
        stack="node",
        runtime=runtime,
        runtime_source=runtime_source,
        dependency_files=dependency_files,
        lockfile=lockfile,
        package_manager=cast("NodeProfile.__annotations__['package_manager']", package_manager),
        package_manager_source=package_manager_source,
        package_manager_spec=package_manager_spec,
        test_command=test_command,
        test_script=test_script,
        package_name=package_name,
        typescript=typescript,
        test_files=test_files,
        confidence=cast("NodeProfile.__annotations__['confidence']", confidence),
        signals=signals,
    )


def _safe_artifact_path(path: object) -> str:
    value = _string(path, "artifact.path")
    if not value or "\\" in value:
        raise ArtifactValidationError("artifact path must be a non-empty POSIX path")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or ".." in parsed.parts or parsed.as_posix() != value:
        raise ArtifactValidationError(f"unsafe artifact path: {value}")
    return value


def _validate_artifacts(
    role: AgentRole,
    value: object,
) -> tuple[Artifact, ...]:
    data = _require_mapping(value, "agent response")
    _require_exact_keys(data, frozenset({"role", "artifacts"}), "agent response")
    raw_artifacts = data["artifacts"]
    if not isinstance(raw_artifacts, list):
        raise AgentProtocolError("artifacts must be an array")
    allowed = _ROLE_ALLOWLIST[role]
    artifacts: list[Artifact] = []
    seen: set[str] = set()
    for index, raw_artifact in enumerate(raw_artifacts):
        artifact = _require_mapping(raw_artifact, f"artifacts[{index}]")
        _require_exact_keys(
            artifact,
            frozenset({"path", "content", "reason"}),
            f"artifacts[{index}]",
        )
        path = _safe_artifact_path(artifact["path"])
        if path not in allowed:
            raise ArtifactValidationError(
                f"{role} is not allowed to emit artifact: {path}"
            )
        if path in seen:
            raise ArtifactValidationError(f"duplicate artifact path: {path}")
        seen.add(path)
        artifacts.append(
            Artifact(
                path=path,
                content=_string(artifact["content"], f"artifacts[{index}].content"),
                reason=_string(artifact["reason"], f"artifacts[{index}].reason"),
            )
        )
    return tuple(artifacts)


def _coerce_role(value: object) -> AgentRole:
    role = _string(value, "agent response.role")
    if role not in AGENT_ROLES:
        raise AgentProtocolError(f"unknown agent role: {role}")
    return cast(AgentRole, role)


def validate_response(value: object, expected_role: AgentRole) -> AgentResponse:
    """Validate a response from either a runner or a raw JSON fake."""

    if isinstance(value, AgentResponse):
        if value.role != expected_role:
            raise AgentProtocolError(
                f"response role mismatch: expected {expected_role}, got {value.role}"
            )
        if expected_role == "stack-detector":
            if value.profile is None or value.artifacts:
                raise AgentProtocolError("stack-detector must return only profile")
            if not isinstance(value.profile, (PythonProfile, NodeProfile)):
                raise AgentProtocolError("stack-detector profile is malformed")
            validate_profile(asdict(value.profile))
            return value
        if value.profile is not None:
            raise AgentProtocolError(f"{expected_role} must not return profile")
        if not isinstance(value.artifacts, (list, tuple)) or not all(
            isinstance(artifact, Artifact) for artifact in value.artifacts
        ):
            raise AgentProtocolError(f"{expected_role} artifacts are malformed")
        _validate_artifacts(
            expected_role,
            {
                "role": value.role,
                "artifacts": [asdict(artifact) for artifact in value.artifacts],
            },
        )
        return value

    if isinstance(value, Mapping):
        data = value
    elif isinstance(value, str):
        data = _decode_json(value)
    else:
        raise AgentProtocolError("agent response must be JSON text or a structured response")
    role = _coerce_role(data.get("role"))
    if role != expected_role:
        raise AgentProtocolError(
            f"response role mismatch: expected {expected_role}, got {role}"
        )
    if role == "stack-detector":
        _require_exact_keys(data, frozenset({"role", "profile"}), "agent response")
        return AgentResponse(role=role, profile=validate_profile(data["profile"]))
    return AgentResponse(role=role, artifacts=_validate_artifacts(role, data))


def _decode_json(output: str) -> Mapping[str, object]:
    text = output.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) < 3 or not lines[0].strip().lower() in {"```", "```json"}:
            raise AgentProtocolError("agent response must be a JSON object or fenced JSON")
        if lines[-1].strip() != "```":
            raise AgentProtocolError("agent response has an unclosed JSON fence")
        text = "\n".join(lines[1:-1]).strip()
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AgentProtocolError("agent response was not valid JSON") from exc
    return _require_mapping(loaded, "agent response")


class OmniRushSubprocessRunner:
    """Run one read-only OmniRush prompt in the isolated snapshot."""

    def __init__(self, binary: str | None = None):
        self.binary = binary or os.environ.get("OMNIRUSH_BIN") or "omnirush"
        self._active_lock = threading.Lock()
        self._active: dict[AgentRole, subprocess.Popen[bytes]] = {}

    def run(
        self,
        request: AgentRequest,
        progress: ProgressCallback | None = None,
    ) -> AgentResponse:
        try:
            process = subprocess.Popen(
                [self.binary, "-p", request.prompt],
                cwd=request.root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                close_fds=True,
            )
        except OSError as exc:
            raise AgentProcessError(
                f"{request.role} could not start OmniRush subprocess"
            ) from exc

        with self._active_lock:
            self._active[request.role] = process

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        def drain(stream: object, parts: list[str], channel: str) -> None:
            assert hasattr(stream, "read")
            while True:
                chunk = stream.read(4096)  # type: ignore[union-attr]
                if not chunk:
                    return
                if isinstance(chunk, bytes):
                    chunk = chunk.decode("utf-8", errors="replace")
                parts.append(chunk)
                _emit(progress, request.role, "output", f"{channel} output received")

        stdout_thread = threading.Thread(
            target=drain,
            args=(process.stdout, stdout_parts, "stdout"),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=drain,
            args=(process.stderr, stderr_parts, "stderr"),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        try:
            process.wait(timeout=request.timeout)
        except subprocess.TimeoutExpired as exc:
            self._terminate(process)
            raise AgentTimeoutError(
                f"{request.role} timed out after {request.timeout:g}s"
            ) from exc
        except Exception:
            if process.poll() is None:
                self._terminate(process)
            raise
        finally:
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
            with self._active_lock:
                if self._active.get(request.role) is process:
                    del self._active[request.role]

        if process.returncode != 0:
            raise AgentProcessError(
                f"{request.role} OmniRush subprocess exited with status {process.returncode}"
            )
        return validate_response("".join(stdout_parts), request.role)

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            try:
                process.terminate()
            except OSError:
                pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                process.kill()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def cancel(self, request: AgentRequest) -> None:
        """Terminate an active role when orchestration cancels the run."""

        with self._active_lock:
            process = self._active.get(request.role)
        if process is not None and process.poll() is None:
            self._terminate(process)


class InProcessAgentRunner:
    """Generate role-scoped responses without credentials or subprocesses."""

    def run(
        self,
        request: AgentRequest,
        progress: ProgressCallback | None = None,
    ) -> AgentResponse:
        _emit(progress, request.role, "output", "in-process response generated")
        if request.role == "stack-detector":
            return AgentResponse(role=request.role, profile=request.profile)
        artifacts = generate_artifacts(request.root, request.profile)
        allowed = _ROLE_ALLOWLIST[request.role]
        return AgentResponse(
            role=request.role,
            artifacts=tuple(artifact for artifact in artifacts if artifact.path in allowed),
        )


def role_allowlist(role: AgentRole) -> frozenset[str]:
    """Expose the immutable allowlist for tests and controller diagnostics."""

    return _ROLE_ALLOWLIST[role]
