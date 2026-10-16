# Phase 2 Context: Node and TypeScript Path

## Goal

Extend the existing isolated pipeline so Node.js and TypeScript repositories receive the same patch-and-report workflow as Python repositories without regressing the Python path.

## Locked decisions

- Keep the existing CLI shape and output names.
- Detect Node/TypeScript repositories from `package.json` and reject ambiguous repositories that also present strong Python metadata.
- Support npm first, then pnpm and Yarn when their lockfiles or `packageManager` metadata make the choice clear.
- Preserve an existing lockfile and package manager. Do not rewrite application scripts unless adding the `make test` wrapper requires it.
- Prefer an existing `test`, `test:ci`, or equivalent package script. Fall back to the Node built-in test runner only when test files provide a clear signal.
- Use Node 22 as the default runtime when no repository declaration exists, with a pinned `.nvmrc` artifact.
- Use a Node slim Docker base and install `make` only if the generated image needs it.
- Keep the output artifact names stable: `Dockerfile`, `Makefile`, `.nvmrc`, dependency proposal when needed, and `README.repro-doctor.md`.
- Keep the generation boundary injectable. Real parallel OmniRush integration remains Phase 3.

## Detection policy

Recognize:

- `package.json`;
- `package-lock.json` and `npm-shrinkwrap.json`;
- `pnpm-lock.yaml`;
- `yarn.lock`;
- `packageManager` and `engines.node` fields;
- `.nvmrc`;
- TypeScript configuration and common test file names.

Select package manager in this order:

1. explicit `packageManager` field;
2. lockfile signal;
3. npm default.

Reject a repository with both strong Python and Node metadata instead of guessing.

## Artifact policy

- Existing Dockerfiles and Makefiles are preserved where possible.
- A missing Makefile receives a `test` target that invokes the detected package script.
- A missing runtime marker receives `.nvmrc` with the selected exact version.
- Existing lockfiles are reported as usable dependency locks.
- A repository with no lockfile receives a dependency-lock proposal rather than an unverified claim of exact reproducibility.

## Verification policy

Phase 2 verification is local and fixture-based. Docker execution remains Phase 4. The project `make test` command must continue to pass after the Node path is added.
