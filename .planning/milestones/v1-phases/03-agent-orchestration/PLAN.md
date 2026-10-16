# Phase 3 Plan: Parallel OmniRush Agent Orchestration

## Plan metadata

- **Phase:** 3
- **Mode:** concurrent subprocess integration
- **Risk:** high; process lifecycle, untrusted output, and artifact conflicts
- **Verification depth:** fake-runner tests plus real CLI discovery/help checks

## Work items

### 1. Define agent and progress models

Add role names, agent responses, artifact validation errors, progress events, and runner protocols without coupling the rest of the pipeline to OmniRush.

### 2. Implement the OmniRush subprocess adapter

Start `omnirush -p` once per role in the isolated repository directory. Stream stdout/stderr, apply a timeout, capture exit status, and parse structured JSON responses.

### 3. Implement parallel orchestration

Launch all four roles with a bounded executor, emit progress through a callback, validate each response, and combine writer artifacts deterministically. Keep the stack detector result advisory against the local profile.

### 4. Integrate agent mode into the pipeline and CLI

Add an explicit agent/local mode. Make agent mode the user-facing default while preserving a local mode for offline tests and environments without OmniRush credentials.

### 5. Add fake-runner and contract tests

Cover concurrency, progress ordering, timeout/failure handling, malformed output, role allowlists, duplicate paths, and successful artifact materialization.

## Verification commands

```bash
make test
python -m repro_doctor --help
command -v omnirush
git diff --check
```

## Completion evidence

Phase 3 is complete only when fake parallel runs are covered by tests, the CLI exposes the two modes and timeout behavior, and real OmniRush availability is reported accurately without being required by the test suite.
