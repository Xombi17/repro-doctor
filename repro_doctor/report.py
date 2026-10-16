from __future__ import annotations

from .models import NodeProfile, Profile


def render_report(
    profile: Profile,
    changed_files: tuple[str, ...],
    *,
    retry_count: int = 0,
    verification_result: str = "not run",
) -> str:
    files = "\n".join(f"- `{path}`" for path in changed_files) or "- (none)"
    commands = "\n".join(
        (
            "- `make test` (available in the generated snapshot; not run by the CLI)",
            "- `docker build -t repro-doctor-target .` (deferred to Phase 4)",
            "- `docker run --rm repro-doctor-target` (deferred to Phase 4)",
        )
    )
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

- Result: {verification_result}
- Retry count: {retry_count}
"""
