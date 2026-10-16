# Phase 4 Plan: Docker Verification and Bounded Repair Loop

## Plan metadata

- **Phase:** 4
- **Mode:** injectable Docker subprocess plus bounded repair controller
- **Risk:** high; process termination, retry semantics, and preserving failed outputs
- **Verification depth:** fake Docker/agent runners plus CLI and report assertions

## Work items

### 1. Define verifier and repair result models

Add command results, verification results, failure classifications, and repair outcome data without coupling core logic to Docker or OmniRush.

### 2. Implement the Docker command runner

Run `docker build` and `docker run --rm IMAGE make test` with captured stdout/stderr, bounded timeouts, safe image tags, and process-group cleanup. Make the runner injectable.

### 3. Implement failure classification and focused repair prompts

Classify build, dependency-install, and test failures locally. Build validated repair requests using the existing writer roles and response allowlists.

### 4. Implement the bounded verification/repair controller

Verify once, repair and rematerialize after a failure, retry at most five times, preserve the last snapshot, and return structured failure information instead of discarding patch/report output.

### 5. Integrate pipeline, report, and CLI behavior

Run verification after generation for CLI runs, add `--skip-verification`, report commands/output/retries/failure details, and return non-zero when verification does not pass.

### 6. Add fake-runner tests

Cover zero-retry success, one-retry repair, exactly-five retry exhaustion, hung command termination, repair routing, output preservation, and CLI non-zero behavior with generated files present.

## Verification commands

```bash
make test
python -m repro_doctor --help
git diff --check
```

## Completion evidence

Phase 4 is complete only when fake Docker tests exercise all retry paths, timeout cleanup is covered, failed verification still emits patch/report files, and the project test suite remains green without Docker.
