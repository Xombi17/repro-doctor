# Project State

## Current position

- **Milestone:** v1 — reproducible Python and Node/TypeScript repositories
- **Current phase:** 2 — Node and TypeScript path
- **Status:** Phase 1 complete; Phase 2 ready to plan
- **Next action:** discuss and plan Phase 2

## Confirmed decisions

- Use a temporary working copy for every input.
- Emit a unified patch and Markdown report.
- Keep Python and Node/TypeScript as separate detection paths.
- Start the four generation roles concurrently.
- Run verification after generation.
- Enforce a maximum of five repair retries.
- Inject agent and Docker runners so the core logic remains testable without external services.

## Open decisions to resolve during phase planning

- Exact lockfile generation strategy for Python projects without a lockfile.
- Supported minimum Node version and default image tag when the target omits a runtime declaration.
- Whether a verifier diagnosis is returned by the OmniRush verifier role or performed by the local controller with an agent-assisted classifier.
- Exact patch behavior for local repositories containing uncommitted or ignored files.

## Verification record

- Phase 1 `make test`: passed, 11 tests.
- Phase 1 fixture patch application: passed.
- Phase 1 source immutability check: passed.
- Project Docker build: attempted; local command timed out while fetching image metadata after 120 seconds. This is not counted as a passing check.
