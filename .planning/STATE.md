# Project State

## Current position

- **Milestone:** v1 — reproducible Python and Node/TypeScript repositories
- **Current phase:** 1 — foundation and Python path
- **Status:** project initialized; implementation not started
- **Next action:** run `/gsd-plan-phase 1`

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

No project checks have run yet. The planning artifacts are the first project files.
