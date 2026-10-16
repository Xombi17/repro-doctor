# Phase 2 Summary: Node and TypeScript Path

## Implemented

- Added a typed `NodeProfile` and a `Profile` union while retaining the existing `PythonProfile` model.
- Added Node/TypeScript detection from `package.json`, package scripts, lockfiles, `packageManager`, `engines.node`, `.nvmrc`, TypeScript configuration/source, and common test-file layouts.
- Added deterministic package-manager selection: explicit `packageManager`, then a supported lockfile (`npm-shrinkwrap.json`/`package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock`), then npm default. Conflicting lockfile families fail with an actionable ambiguity error.
- Added runtime selection from `.nvmrc`, then `engines.node`, then the pinned Node 22 fallback.
- Added package test-script selection for `test`, `test:ci`, equivalent test scripts, existing Makefile targets, and the Node built-in runner when test files provide a clear signal.
- Added stack dispatch in the pipeline and Node-aware reporting/CLI output without changing the Python artifact path.
- Added Node artifact generation for a package-manager-aware slim Dockerfile, `Makefile`, `.nvmrc`, no-lockfile dependency proposal, and `README.repro-doctor.md`. Existing Dockerfiles, Makefiles, runtime markers, and usable lockfiles remain preserved.
- Added npm and TypeScript fixtures plus focused coverage for npm lockfiles, no-lockfile TypeScript, pnpm/Yarn lockfile selection, explicit package-manager precedence, Node 22 fallback, artifact contents, patch application, and source immutability.
- Updated the project README to describe Python and Node.js/TypeScript support.

## Evidence

- `make test` — passed: 20 tests, `OK`.
- `python -m compileall -q repro_doctor tests` — passed with no output.
- `python -m repro_doctor --help` — passed; usage and Python/Node.js repository description printed.
- `git diff --check` — passed with no output.
- Node pipeline fixture test — passed `git apply --check` against a clean fixture copy and confirmed the source fixture digest was unchanged.

## Scope notes

- Docker execution and generated-repository verification were not run; they remain deferred to the Docker verification phase.
- No OmniRush subprocess or real parallel orchestration was added; the generation boundary remains in-process and injectable for Phase 3.
- No unrelated planning files were changed.

## Commit

- `83105cf feat: add node repository path`
