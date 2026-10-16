# Phase 5 Plan: Tests, Documentation, and Release Readiness

## Plan metadata

- **Phase:** 5
- **Mode:** reproducibility validation and documentation hardening
- **Risk:** medium; clean-clone drift and inaccurate operational instructions
- **Verification depth:** fresh-copy test execution, docs consistency tests, CLI checks, and Docker build attempt

## Work items

### 1. Add clean-clone and release-readiness tests

Exercise `make test` and CLI help from a fresh repository copy without relying on the source checkout's caches or generated output. Add assertions for pinned runtime/dependencies, required project files, and source immutability boundaries.

### 2. Complete supported-repository and contribution documentation

Document supported Python and Node/TypeScript metadata, package-manager/lockfile policy, generated outputs, verification/repair behavior, limitations, contribution workflow, and safe local testing.

### 3. Add report examples and requirement traceability

Check in redacted Python and Node report examples plus a release checklist mapping v1 requirements to code/tests/evidence and identifying any environment-dependent checks.

### 4. Validate exact commands and repository artifacts

Run the real `make test`, compile checks, CLI help, documentation tests, `git diff --check`, and the documented Docker build. Fix drift found by the checks.

### 5. Record completion evidence

Write the phase summary with actual commands and results, including any Docker daemon or registry blocker, without claiming an unrun check passed.

## Verification commands

```bash
make test
python -m compileall -q repro_doctor tests
python -m repro_doctor --help
docker build -t repro-doctor .
git diff --check
```

## Completion evidence

Phase 5 is complete when clean-copy tests and documentation checks pass, the repository contains exact setup/run/test/Docker/deploy guidance, report examples and release traceability are present, and all environment-dependent validation is recorded honestly.
