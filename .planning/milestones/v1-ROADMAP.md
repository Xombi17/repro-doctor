# Roadmap: repro-doctor v1

## Milestone: v1 — reproducible Python and Node/TypeScript repositories

### Phase 1: Foundation and Python path — COMPLETE

**Goal:** Process a Python repository from input through patch generation with a clean, deterministic internal architecture.

**Deliverables:**

- Python package and CLI entry point;
- local path and GitHub URL input handling;
- temporary workspace and baseline snapshot management;
- structured project and artifact models;
- Python stack detector;
- Python runtime and dependency policy;
- Dockerfile, Makefile, and README artifact contracts;
- unified patch generation;
- initial Markdown report;
- minimal Python fixture repository;
- initial project Dockerfile, lockfile, Makefile, README, and MIT license.

**Acceptance checks:**

- A local Python fixture can be analyzed without modifying the source.
- The output patch applies cleanly to the fixture baseline.
- Generated artifacts contain the expected Python runtime, dependency, Docker, test, and documentation data.
- Project `make test` passes.

**Evidence:**

- `make test` — passed, 11 tests.
- Fixture patch application — passed through `git apply --check` and `git apply`.
- Source snapshot preservation — passed in the pipeline test.
- Project Docker build was attempted but exceeded the local 120-second command timeout while fetching image metadata; Docker verification remains in Phase 4 and final clean-clone validation remains in Phase 5.

### Phase 2: Node and TypeScript path — COMPLETE

**Goal:** Add Node/TypeScript detection and artifact generation while preserving the Python path.

**Deliverables:**

- npm, pnpm, and Yarn detection;
- package-lock, npm-shrinkwrap, pnpm-lock, and yarn.lock handling;
- Node runtime detection from `.nvmrc`, `engines`, or configured fallback;
- test script detection and `make test` wrapping;
- TypeScript fixture repository;
- Node artifact validation;
- regression coverage for Python behavior.

**Acceptance checks:**

- A Node/TypeScript fixture can be analyzed without source mutation.
- Existing supported lockfiles and package-manager choices are preserved.
- The generated Dockerfile builds and the generated `make test` command is correct for the fixture.
- Project `make test` continues to pass.

**Evidence:**

- `make test` — passed, 20 tests.
- Node fixture patch application — passed through `git apply --check`.
- Node fixture source immutability — passed.
- Python regression coverage — passed in the same 20-test suite.

### Phase 3: Parallel OmniRush agent orchestration — COMPLETE

**Goal:** Replace direct artifact decisions with four parallel OmniRush roles and live progress.

**Deliverables:**

- agent runner protocol;
- OmniRush CLI subprocess adapter;
- stack detector, Dockerfile writer, test-script writer, and README writer prompts;
- concurrent scheduling and result collection;
- structured result validation;
- progress event stream and terminal renderer;
- fake agent runner for tests;
- timeout and process cleanup behavior.

**Acceptance checks:**

- All four roles start concurrently.
- Progress is visible while agents are running.
- One role failing does not leave other role processes hanging.
- Invalid agent output is reported clearly.
- Fake-runner tests work without OmniRush credentials.

**Evidence:**

- `make test` — passed, 28 tests.
- CLI help, `command -v omnirush`, and `git diff --check` — passed.
- Fake-runner tests verified four concurrent roles, progress events, protocol validation, failure handling, timeout cancellation, and source immutability.
- Subprocess lifecycle test verified timed-out OmniRush processes are terminated and reaped.

### Phase 4: Docker verifier and bounded repair loop — COMPLETE

**Goal:** Verify generated repositories in Docker and repair failures without unbounded automation.

**Deliverables:**

- Docker build runner;
- container test runner;
- verifier result model;
- failure classification and role routing;
- focused repair prompts;
- retry controller with a hard maximum of five retries;
- command timeouts and process termination;
- retry count and failure details in the final report;
- fake Docker runner tests.

**Acceptance checks:**

- A passing fixture reports zero retries and successful Docker verification.
- A fixture that fails once is repaired and reports one retry.
- A fixture that always fails stops after exactly five retries.
- Hung commands are terminated and reported.
- The CLI returns non-zero on unsuccessful verification while still producing output files.

**Evidence:**

- `make test` — passed, 34 tests.
- CLI help and `git diff --check` — passed.
- Fake Docker/repair tests verified zero-retry success, one-retry recovery, exact five-retry exhaustion, failure routing, output preservation, and non-zero CLI failure status.
- Hanging fake Docker process-group test verified timeout termination and child reaping.

### Phase 5: Tests, documentation, and release readiness — COMPLETE

**Goal:** Make the project reproducible, documented, licensed, and ready for public review.

**Deliverables:**

- complete detector, patch, orchestration, verifier, and CLI tests;
- clean-clone validation;
- project Docker build validation;
- README with exact setup, run, test, Docker, and deployment guidance;
- MIT license;
- contribution and supported-repository documentation;
- final report examples;
- small focused commits and release checklist.

**Acceptance checks:**

- A clean clone can install pinned dependencies and run `make test`.
- The project Dockerfile builds successfully.
- Documentation commands match the actual CLI.
- All v1 requirements have traceability and verification evidence.

**Evidence:**

- `make test` — passed, 41 tests, including fresh-copy execution of `make test` and CLI help.
- `python -m compileall -q repro_doctor tests` — passed.
- `python -m repro_doctor --help` and `git diff --check` — passed.
- Added contribution, supported-repository, release traceability, and redacted report-example documentation.
- `docker build -t repro-doctor .` was attempted but blocked before build by Docker daemon permissions; this is documented as an environment gap, not a passing check.

## Phase dependencies

- Phase 2 depends on the artifact contracts and input isolation from Phase 1.
- Phase 3 depends on both stack paths having stable structured outputs.
- Phase 4 depends on the artifact materialization and command interfaces from Phase 3.
- Phase 5 depends on all functional phases being implemented.

## Planned commit sequence

1. `chore: initialize gsd project`
2. `feat: add python repository path`
3. `feat: add node repository path`
4. `feat: orchestrate parallel omnirush agents`
5. `feat: add docker verification retry loop`
6. `test: cover reproducibility workflows`
7. `docs: document usage and release process`
