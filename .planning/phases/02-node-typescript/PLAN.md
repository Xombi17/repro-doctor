# Phase 2 Plan: Node and TypeScript Path

## Plan metadata

- **Phase:** 2
- **Mode:** vertical tracer-first extension
- **Risk:** medium; detector and artifact models must remain compatible with Python
- **Verification depth:** fixture tests plus full project `make test`

## Work items

### 1. Generalize project profiles and pipeline dispatch

Add a typed Node profile and route detection/generation by stack while preserving the current Python behavior and output model.

### 2. Implement Node package metadata detection

Parse package scripts, runtime declarations, package manager signals, lockfiles, TypeScript configuration, and test file layouts. Return actionable unsupported/ambiguous errors.

### 3. Implement Node artifact generation

Generate a package-manager-aware Dockerfile, `Makefile`, `.nvmrc`, dependency proposal where needed, and reproducibility README artifact. Preserve existing project files and lockfiles.

### 4. Add Node fixture coverage

Create npm and TypeScript fixture cases, including an existing package lock and a no-lockfile case. Exercise test script selection and source immutability.

### 5. Run regression verification

Run the full test suite, CLI help, patch application tests, and static checks. Update phase summary and project state with actual evidence.

## Verification commands

```bash
make test
python -m repro_doctor --help
git diff --check
```

## Completion evidence

Phase 2 is complete only when Python tests still pass, Node fixtures generate applyable patches, package-manager selection is deterministic, and the source fixtures remain unchanged.
