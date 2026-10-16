# Phase 4 Context: Docker Verification and Bounded Repair

## Goal

Verify the materialized reproducibility artifacts in Docker, route failures to a focused repair role, and stop deterministically after a maximum of five repair retries while preserving the patch and report on failure.

## Locked decisions

- Verification runs against the isolated materialized snapshot, after generation and before the patch is written.
- Use an injectable Docker runner for offline tests and a subprocess-backed runner for real `docker build` and `docker run --rm IMAGE make test` commands.
- Build and test commands have bounded timeouts; timed-out process groups are terminated and reaped.
- Keep verification and repair result data structured, including stage, captured output, classification, retry count, and final status.
- Classify failures locally from the command stage and output; do not require a separate verifier agent for diagnosis.
- Route build and dependency-install failures to `dockerfile-writer`; route test-command failures to `test-script-writer`.
- Repair calls reuse the validated writer response contract and role allowlists from Phase 3. A repair may return only files in its assigned scope and may not edit application source files.
- The retry limit is exactly five repair attempts. A successful first verification reports zero retries; a failure after five repairs reports five retries.
- Verification failure still writes the final patch and Markdown report, and the CLI returns a non-zero status.
- Direct library callers retain verification opt-in for backward-compatible offline tests; the CLI enables verification by default and offers an explicit `--skip-verification` escape hatch for local development.

## Out of scope

- Docker image publishing or registry authentication.
- Repairing application behavior or arbitrary test failures.
- More than one repair role per failed attempt.
- Cloud verification or remote Docker execution.
