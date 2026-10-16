from __future__ import annotations

import math
from pathlib import Path
import threading
import time
from typing import cast

from .agents import (
    AGENT_ROLES,
    DEFAULT_AGENT_TIMEOUT,
    AgentRunner,
    OmniRushSubprocessRunner,
    _planned_paths,
    build_role_prompt,
    role_allowlist,
    validate_response,
)
from .errors import (
    AgentError,
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
    Profile,
    ProgressCallback,
    ProgressEvent,
)


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
        return


def _run_role(
    runner: AgentRunner,
    request: AgentRequest,
    progress: ProgressCallback | None,
) -> AgentResponse:
    response = runner.run(request, progress)
    # The real adapter validates before returning. Keeping this second boundary
    # allows fakes to return raw JSON and keeps the controller authoritative.
    return validate_response(response, request.role)


def _cancel_role(runner: AgentRunner, request: AgentRequest) -> None:
    cancel = getattr(runner, "cancel", None)
    if not callable(cancel):
        return
    try:
        cancel(request)
    except Exception:
        # Cancellation is best effort for injected runners. The real subprocess
        # adapter implements it and owns the process lifecycle.
        return


def _wait_for_roles(events: dict[AgentRole, threading.Event], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        if all(event.is_set() for event in events.values()):
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        for event in events.values():
            if not event.is_set():
                event.wait(min(remaining, 0.01))


def _runner_progress(
    progress: ProgressCallback | None,
    role: AgentRole,
    cancelled: set[AgentRole],
    cancelled_lock: threading.Lock,
) -> ProgressCallback | None:
    if progress is None:
        return None

    def forward(event: ProgressEvent) -> None:
        with cancelled_lock:
            if role in cancelled:
                return
        if event.role == role:
            try:
                progress(event)
            except Exception:
                return

    return forward


def orchestrate_generation(
    root: Path,
    profile: Profile,
    *,
    runner: AgentRunner | None = None,
    timeout: float = DEFAULT_AGENT_TIMEOUT,
    progress: ProgressCallback | None = None,
) -> tuple[Artifact, ...]:
    """Run exactly four role requests concurrently and collect safe artifacts."""

    if not math.isfinite(timeout) or timeout <= 0:
        raise AgentProtocolError("agent timeout must be greater than zero")
    selected_runner = runner or OmniRushSubprocessRunner()
    requests = {
        role: AgentRequest(
            role=role,
            root=root,
            profile=profile,
            prompt=build_role_prompt(role, root, profile),
            timeout=timeout,
        )
        for role in AGENT_ROLES
    }

    responses: dict[AgentRole, AgentResponse] = {}
    errors: dict[AgentRole, Exception] = {}
    done_events = {role: threading.Event() for role in AGENT_ROLES}
    cancelled: set[AgentRole] = set()
    cancelled_lock = threading.Lock()

    def run_role(role: AgentRole) -> None:
        try:
            responses[role] = _run_role(
                selected_runner,
                requests[role],
                _runner_progress(progress, role, cancelled, cancelled_lock),
            )
        except Exception as exc:
            errors[role] = exc
        finally:
            done_events[role].set()

    for role in AGENT_ROLES:
        _emit(progress, role, "start", "started")
    for role in AGENT_ROLES:
        thread = threading.Thread(
            target=run_role,
            args=(role,),
            name=f"repro-agent-{role}",
            daemon=True,
        )
        thread.start()

    deadline = time.monotonic() + timeout
    failure_seen = False
    while True:
        if any(done_events[role].is_set() and role in errors for role in AGENT_ROLES):
            failure_seen = True
            break
        if all(event.is_set() for event in done_events.values()):
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(0.005)

    timed_out: set[AgentRole] = set()
    if failure_seen:
        with cancelled_lock:
            pending = {
                role for role in AGENT_ROLES if not done_events[role].is_set()
            }
            cancelled.update(pending)
        for role in pending:
            _cancel_role(selected_runner, requests[role])
        _wait_for_roles(
            {role: done_events[role] for role in pending},
            min(1.0, max(0.1, timeout)),
        )
    elif not all(event.is_set() for event in done_events.values()):
        timed_out = {
            role for role in AGENT_ROLES if not done_events[role].is_set()
        }
        with cancelled_lock:
            cancelled.update(timed_out)
        for role in timed_out:
            _emit(progress, role, "timeout", f"timed out after {timeout:g}s")
            _cancel_role(selected_runner, requests[role])
        _wait_for_roles(
            {role: done_events[role] for role in timed_out},
            min(1.0, max(0.1, timeout)),
        )

    failures: list[tuple[AgentRole, Exception]] = []
    for role in AGENT_ROLES:
        if role in timed_out:
            failures.append(
                (role, AgentTimeoutError(f"{role} timed out after {timeout:g}s"))
            )
            continue
        error = errors.get(role)
        if error is not None:
            if isinstance(error, AgentTimeoutError):
                _emit(progress, role, "timeout", str(error))
            else:
                _emit(progress, role, "failed", _safe_failure_detail(error))
            failures.append((role, error))
            continue
        if role in responses:
            _emit(progress, role, "complete", "response received and validated")
            continue
        if failure_seen:
            detail = "cancelled after another role failed"
            _emit(progress, role, "failed", detail)
            failures.append((role, AgentError(f"{role} was cancelled")))
        else:
            error = AgentError(f"{role} did not return a response")
            _emit(progress, role, "failed", str(error))
            failures.append((role, error))

    if failures:
        first_role, first_error = failures[0]
        if isinstance(first_error, AgentError):
            raise first_error
        raise AgentError(
            f"agent generation failed in {first_role}: {_safe_failure_detail(first_error)}"
        ) from first_error

    planned_paths = set(_planned_paths(root, profile))
    combined: list[Artifact] = []
    seen: dict[str, AgentRole] = {}
    for role in AGENT_ROLES:
        response = responses[role]
        if role == "stack-detector":
            if response.profile is None:
                raise AgentProtocolError("stack-detector returned no profile")
            if response.profile.stack != profile.stack:
                _emit(progress, role, "failed", "advisory profile stack mismatch")
                raise AgentProtocolError(
                    "stack-detector returned a profile for a different stack"
                )
            continue
        required_paths = planned_paths.intersection(role_allowlist(role))
        returned_paths = {artifact.path for artifact in response.artifacts}
        missing_paths = required_paths - returned_paths
        if missing_paths:
            missing = ", ".join(sorted(missing_paths))
            raise AgentProtocolError(
                f"{role} omitted deterministic artifacts required by the plan: {missing}"
            )
        for artifact in response.artifacts:
            if artifact.path not in planned_paths:
                raise ArtifactValidationError(
                    f"{role} returned an artifact not requested by the deterministic plan: {artifact.path}"
                )
            previous_role = seen.get(artifact.path)
            if previous_role is not None:
                raise AgentProtocolError(
                    f"duplicate artifact path {artifact.path} from {previous_role} and {role}"
                )
            seen[artifact.path] = role
            combined.append(artifact)
    return tuple(combined)


def _safe_failure_detail(error: Exception) -> str:
    if isinstance(error, AgentProtocolError):
        return str(error)
    if isinstance(error, AgentTimeoutError):
        return str(error)
    return str(error) or error.__class__.__name__
