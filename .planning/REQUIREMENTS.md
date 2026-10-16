# Requirements: repro-doctor v1

## Functional requirements

### Input and isolation

- **REQ-001**: The CLI must accept a local repository path.
- **REQ-002**: The CLI must accept a GitHub HTTPS URL and clone it into a temporary workspace.
- **REQ-003**: The CLI must reject unsupported or ambiguous repositories with an actionable error.
- **REQ-004**: The CLI must not modify the original local repository.
- **REQ-005**: The CLI must support a deterministic output directory for the patch and report.

### Stack detection

- **REQ-010**: The CLI must detect Python repositories from common metadata including `pyproject.toml`, requirements files, Poetry/uv metadata, and Python test layouts.
- **REQ-011**: The CLI must detect Node/TypeScript repositories from `package.json`, lockfiles, runtime metadata, and test scripts.
- **REQ-012**: The detector must identify the package manager and preserve it when it is supported.
- **REQ-013**: The detector must identify an existing test command before proposing a fallback.
- **REQ-014**: The detector must identify or propose a pinned runtime version.
- **REQ-015**: The detector must return structured data that can be passed to all writer agents.

### Agent orchestration

- **REQ-020**: The CLI must launch a stack detector, Dockerfile writer, test-script writer, and README writer in parallel.
- **REQ-021**: Each agent must receive a self-contained role prompt and repository context.
- **REQ-022**: Agent results must be structured and validated before being materialized.
- **REQ-023**: Agent output must not cause unrelated source changes.
- **REQ-024**: The CLI must print live start, progress, completion, and failure events for each role.
- **REQ-025**: The OmniRush integration must be replaceable with a fake runner for tests.
- **REQ-026**: Agent calls must have bounded timeouts and clear failure handling.

### Generated reproducibility artifacts

- **REQ-030**: The patch must add or repair pinned dependency information.
- **REQ-031**: The patch must add or repair a pinned runtime declaration when the repository lacks one.
- **REQ-032**: The patch must add a working Dockerfile for the detected stack.
- **REQ-033**: The patch must add a `Makefile` with a `test` target that invokes the repository's test command.
- **REQ-034**: The patch must add or update a README with setup, run, test, and Docker instructions.
- **REQ-035**: The generated files must preserve an existing package manager and usable lockfile.
- **REQ-036**: Dependency installation must occur during image build rather than during `make test`.

### Verification and repair

- **REQ-040**: Verification must build the generated Dockerfile.
- **REQ-041**: Verification must run `make test` inside the generated image.
- **REQ-042**: Verification must run after the four generation roles complete.
- **REQ-043**: A verification failure must include captured command output.
- **REQ-044**: A failure must be routed to the most relevant repair role.
- **REQ-045**: The controller must allow at most five repair retries.
- **REQ-046**: Docker and agent subprocesses must have timeouts so the CLI cannot hang indefinitely.
- **REQ-047**: The CLI must emit a final report when verification fails as well as when it succeeds.

### Outputs

- **REQ-050**: The CLI must emit an applyable unified patch.
- **REQ-051**: The CLI must emit a short Markdown report.
- **REQ-052**: The report must list the detected stack, changed files, verification commands, result, and retry count.
- **REQ-053**: The CLI must return a non-zero exit code when it cannot produce a verified result.

## Project quality requirements

- **REQ-060**: The `repro-doctor` repository must pin its own development dependencies.
- **REQ-061**: The repository must include a Dockerfile that builds the CLI.
- **REQ-062**: The repository must include a single `make test` command.
- **REQ-063**: The repository README must document setup, run, test, and Docker usage.
- **REQ-064**: Core logic must have automated tests using fake agent and Docker runners where external services are unnecessary.
- **REQ-065**: The repository must include an open-source license.
- **REQ-066**: Work must be organized into small, focused commits.

## Non-goals for v1

- **NREQ-001**: No support for runtimes other than Python and Node/TypeScript.
- **NREQ-002**: No automatic cloud deployment.
- **NREQ-003**: No automatic GitHub push or pull-request creation.
- **NREQ-004**: No attempt to repair arbitrary application logic or failing business tests.
- **NREQ-005**: No guarantee for repositories requiring private package registries unless credentials and configuration are already available.

## Traceability targets

| Requirement group | Planned phase |
|---|---|
| REQ-001–005 | Phase 1 |
| REQ-010–015 | Phases 1–2 |
| REQ-020–026 | Phase 3 |
| REQ-030–036 | Phases 1–2 |
| REQ-040–047 | Phase 4 |
| REQ-050–053 | Phases 1 and 4 |
| REQ-060–066 | Phase 5 |
