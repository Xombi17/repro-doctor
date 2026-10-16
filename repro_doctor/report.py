from __future__ import annotations

from .models import PythonProfile


def render_report(
    profile: PythonProfile,
    changed_files: tuple[str, ...],
    *,
    retry_count: int = 0,
    verification_result: str = "not run",
) -> str:
    files = "\n".join(f"- `{path}`" for path in changed_files) or "- (none)"
    commands = "\n".join(
        (
            "- `make test` (available in the generated snapshot; not run by Phase 1 CLI)",
            "- `docker build -t repro-doctor-target .` (deferred to Phase 4)",
            "- `docker run --rm repro-doctor-target` (deferred to Phase 4)",
        )
    )
    return f"""# repro-doctor report

## Detected stack

- Stack: Python
- Package: {profile.package_name or '(not declared)'}
- Runtime: Python {profile.runtime}
- Detection confidence: {profile.confidence}
- Test command: `{profile.test_command}`

## Changed files

{files}

## Verification

{commands}

- Result: {verification_result}
- Retry count: {retry_count}
"""
