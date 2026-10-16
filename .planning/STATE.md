# Project State

## Current position

- **Milestone:** v1 — reproducible Python and Node/TypeScript repositories
- **Current phase:** v1 complete — release readiness
- **Status:** Milestone archived; Docker validation remains environment-dependent and unverified
- **Next action:** start a new milestone with `/gsd-new-milestone` or rerun Docker checks on an accessible daemon

## Confirmed decisions

- Use a temporary working copy for every input.
- Emit a unified patch and Markdown report.
- Keep Python and Node/TypeScript as separate detection paths.
- Start the four generation roles concurrently.
- Run verification after generation.
- Enforce a maximum of five repair retries.
- Inject agent and Docker runners so the core logic remains testable without external services.
- Launch exactly four generation roles concurrently, with deterministic local detection as the materialization baseline.
- Validate agent JSON responses and role-owned artifact paths before materialization.
- Make agent mode the CLI default while retaining explicit local mode for offline tests.
- Use `OMNIRUSH_BIN` and bounded per-role timeouts; terminate active role processes on failure or timeout.
- Diagnose Docker failures locally from stage and captured output, then route one focused repair role per attempt.
- Verify once before repair and allow at most five repair attempts.
- Preserve patch and report output even when verification remains unsuccessful.
- Enable verification by default in the CLI while retaining an explicit skip flag and library opt-in for offline tests.
- Preserve all source files, including uncommitted or ignored files, in the isolated baseline; omit `.git` metadata and emit only generated changes in the patch.
- Keep release evidence honest: Docker checks are environment-dependent and are recorded as unverified when the daemon is inaccessible.

## Open decisions to resolve during phase planning


## Verification record

- Phase 1 `make test`: passed, 11 tests.
- Phase 1 fixture patch application: passed.
- Phase 1 source immutability check: passed.
- Project Docker build: attempted; local command timed out while fetching image metadata after 120 seconds. This is not counted as a passing check.
- Phase 2 `make test`: passed, 20 tests.
- Phase 2 Node fixture patch application and source immutability: passed.
- Phase 3 `make test`: passed, 28 tests.
- Phase 3 fake parallel-runner, protocol-validation, progress, timeout, and subprocess-cleanup checks: passed.
- Phase 4 `make test`: passed, 34 tests.
- Phase 4 fake Docker success, repair, retry exhaustion, failure routing, report preservation, and process-cleanup checks: passed.
- Phase 5 `make test`: passed, 41 tests, including clean-copy validation and post-audit integration regressions.
- Phase 5 compile, CLI help, and diff checks: passed.
- Phase 5 Docker build: attempted; blocked by Docker daemon permission denied and recorded in `RELEASE-CHECKLIST.md`.
