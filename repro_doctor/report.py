from __future__ import annotations

import shlex

from .models import NodeProfile, Profile, VerificationResult


def render_report(
    profile: Profile,
    changed_files: tuple[str, ...],
    *,
    retry_count: int = 0,
    verification_result: str = "not run",
    verification: VerificationResult | None = None,
) -> str:
    files = "\n".join(f"- `{path}`" for path in changed_files) or "- (none)"
    if verification is None:
        commands = "\n".join(
            (
                "- `make test` (available in the generated snapshot; not run)",
                "- `docker build -t repro-doctor-target .` (not run)",
                "- `docker run --rm repro-doctor-target make test` (not run)",
            )
        )
        result_text = verification_result
        report_retry_count = retry_count
        failure_details = ""
        repair_details = ""
    else:
        commands = "\n".join(
            f"- `{shlex.join(result.command)}`"
            for result in verification.commands
        ) or "- (no command result)"
        result_text = verification.status
        report_retry_count = verification.retry_count
        failure_details = ""
        if verification.failure is not None:
            failure = verification.failure
            failure_details = f"""
- Failure stage: `{failure.stage}`
- Failure classification: `{failure.classification}`
- Failed command: `{shlex.join(failure.command)}`
- Captured output:

```text
{failure.output or '(no output)'}
```
"""
        repair_lines = []
        for repair in verification.repairs:
            files_for_attempt = ", ".join(f"`{path}`" for path in repair.changed_files) or "no files"
            state = "materialized" if repair.success else "failed"
            trigger = f"triggered by `{repair.stage}`" if repair.stage else "trigger stage unknown"
            output = f" Captured output: {repair.failure_output}" if repair.failure_output else ""
            repair_lines.append(
                f"- Attempt {repair.attempt}: `{repair.role}` ({repair.classification}) — "
                f"{state}; {files_for_attempt}; {trigger}. {repair.detail}.{output}"
            )
        repair_details = "\n".join(repair_lines) if repair_lines else "- (none)"
    if isinstance(profile, NodeProfile):
        stack = "Node.js / TypeScript" if profile.typescript else "Node.js"
        package = profile.package_name or "(not declared)"
        runtime = f"Node.js {profile.runtime}"
        manager = f"{profile.package_manager} ({profile.package_manager_source})"
    else:
        stack = "Python"
        package = profile.package_name or "(not declared)"
        runtime = f"Python {profile.runtime}"
        manager = None
    manager_line = f"- Package manager: {manager}\n" if manager else ""
    return f"""# repro-doctor report

## Detected stack

- Stack: {stack}
- Package: {package}
- Runtime: {runtime}
{manager_line}- Detection confidence: {profile.confidence}
- Test command: `{profile.test_command}`

## Changed files

{files}

## Verification

{commands}

- Result: {result_text}
- Retry count: {report_retry_count}
{failure_details}
### Repair attempts

{repair_details}
"""
