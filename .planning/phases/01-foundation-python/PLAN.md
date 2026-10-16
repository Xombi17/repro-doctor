# Phase 1 Plan: Foundation and Python Path

## Plan metadata

- **Phase:** 1
- **Mode:** vertical tracer-first slice
- **Risk:** medium; filesystem snapshots and patch generation are shared foundations
- **Verification depth:** targeted unit tests plus project `make test`

## Work items

### 1. Establish the Python project shell

Create the package layout, pinned development dependencies, Dockerfile, Makefile, license, and CLI entry point. Keep the runtime dependency footprint minimal and make the project itself runnable from a clean checkout.

### 2. Implement input isolation

Implement local-directory snapshotting and GitHub URL cloning behind a small input boundary. Reject unsupported URLs and missing paths. Ensure the original local directory is never modified.

### 3. Implement Python detection

Inspect repository metadata and test layouts. Select a test command using existing configuration first, then safe fallbacks. Return typed detection data and actionable unsupported/ambiguous errors.

### 4. Implement artifact generation

Generate reproducibility artifacts from a Python profile. Preserve existing lockfiles and project intent. Add a pinned runtime marker and conservative dependency metadata only when required.

### 5. Implement patch and report generation

Create a baseline snapshot, materialize generated artifacts in a working snapshot, and emit a binary-safe unified patch plus a short Markdown report.

### 6. Add focused tests

Cover detection, input isolation, artifact generation, patch application, report fields, CLI success/failure, and clean project execution.

## Verification commands

```bash
make test
python -m repro_doctor --help
git diff --check
git status --short
```

## Completion evidence

Phase 1 is complete only when the fixture tests pass, `make test` passes, the generated patch applies to a clean fixture, and the source fixture remains unchanged.
