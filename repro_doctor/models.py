from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, TypeAlias


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
class NodeProfile:
    """Structured Node.js or TypeScript repository data."""

    stack: Literal["node"]
    runtime: str
    runtime_source: str
    dependency_files: tuple[str, ...]
    lockfile: str | None
    package_manager: Literal["npm", "pnpm", "yarn"]
    package_manager_source: str
    package_manager_spec: str | None
    test_command: str
    test_script: str | None
    package_name: str | None
    typescript: bool
    test_files: tuple[str, ...]
    confidence: Literal["high", "medium"]
    signals: tuple[str, ...]

    @property
    def is_typescript(self) -> bool:
        """Compatibility-friendly spelling for callers interested in language."""

        return self.typescript


Profile: TypeAlias = PythonProfile | NodeProfile


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
    profile: Profile
    changed_files: tuple[str, ...]
    retry_count: int = 0
    verification_result: str = "not run"
    verification: VerificationResult | None = None


AgentRole: TypeAlias = Literal[
    "stack-detector",
    "dockerfile-writer",
    "test-script-writer",
    "readme-writer",
]
VerificationStage: TypeAlias = Literal["build", "test"]
VerificationStatus: TypeAlias = Literal["passed", "failed"]
FailureClassification: TypeAlias = Literal[
    "build",
    "dependency",
    "test",
    "timeout",
    "unknown",
]
AgentEventKind: TypeAlias = Literal[
    "start",
    "output",
    "complete",
    "failed",
    "timeout",
]


@dataclass(frozen=True)
class ProgressEvent:
    """A safe, role-prefixed update from the agent controller."""

    role: AgentRole
    kind: AgentEventKind
    detail: str


@dataclass(frozen=True)
class CommandResult:
    """Captured result of one bounded external command."""

    command: tuple[str, ...]
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    duration: float = 0.0

    @property
    def output(self) -> str:
        """Return stdout and stderr in the order useful for diagnostics."""

        return "\n".join(part for part in (self.stdout, self.stderr) if part)

    @property
    def succeeded(self) -> bool:
        return not self.timed_out and self.returncode == 0


@dataclass(frozen=True)
class FailureInfo:
    """Local diagnosis for a failed Docker command."""

    stage: VerificationStage
    classification: FailureClassification
    command: tuple[str, ...]
    output: str
    timed_out: bool = False


@dataclass(frozen=True)
class RepairOutcome:
    """One focused repair attempt made after a failed verification."""

    attempt: int
    role: AgentRole
    classification: FailureClassification
    success: bool
    changed_files: tuple[str, ...] = ()
    detail: str = ""
    stage: VerificationStage | None = None
    failure_output: str = ""
    failed_command: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationResult:
    """Structured result for the build/test verification and repair loop."""

    status: VerificationStatus
    image_tag: str
    build_result: CommandResult | None = None
    test_result: CommandResult | None = None
    failure: FailureInfo | None = None
    retry_count: int = 0
    repairs: tuple[RepairOutcome, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    @property
    def commands(self) -> tuple[CommandResult, ...]:
        return tuple(
            result
            for result in (self.build_result, self.test_result)
            if result is not None
        )


@dataclass(frozen=True)
class AgentRequest:
    """A self-contained request sent to one generation role."""

    role: AgentRole
    root: Path
    profile: Profile
    prompt: str
    timeout: float


@dataclass(frozen=True)
class AgentResponse:
    """Validated structured data returned by one generation role."""

    role: AgentRole
    profile: Profile | None = None
    artifacts: tuple[Artifact, ...] = ()


ProgressCallback: TypeAlias = Callable[[ProgressEvent], None]
