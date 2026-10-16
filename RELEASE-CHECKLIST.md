# v1 release and requirement traceability checklist

This checklist records implementation evidence for every v1 requirement. A
checkmark means the behavior is implemented and covered by the named source or
test evidence. Environment-dependent checks are recorded separately and are not
marked successful without observed output.

## Release gates

- [x] `make test` passes from the source checkout and from a fresh temporary
  copy with Git metadata, caches, bytecode, and generated output removed.
- [x] `python -m compileall -q repro_doctor tests` passes.
- [x] `python -m repro_doctor --help` passes and matches the README option table.
- [x] `git diff --check` passes.
- [x] `docker build -t repro-doctor .` was attempted. It did not pass because
  this environment cannot access the Docker daemon; the exact result is below.
- [x] No CI-provider configuration or cloud deployment behavior was added.
- [x] Report examples contain schema fields and no credentials.
- [x] `.env.example` documents safe executable overrides; `.env` is ignored and no secrets are committed.

## Functional traceability

| Requirement | Evidence | Status |
|---|---|---|
| REQ-001 local repository path | `repro_doctor/cli.py`; `tests/test_cli.py::test_success_and_actionable_failure` | [x] |
| REQ-002 GitHub HTTPS input | `repro_doctor/inputs.py`; `tests/test_inputs.py::test_github_url_uses_replaceable_clone_runner` | [x] |
| REQ-003 reject unsupported or ambiguous repositories | `repro_doctor/detect.py`; `tests/test_detection.py` rejection cases and `tests/test_inputs.py` URL rejection | [x] |
| REQ-004 preserve original repository | `repro_doctor/inputs.py`; `tests/test_inputs.py::test_local_snapshot_isolated_and_git_metadata_is_omitted`; pipeline immutability tests | [x] |
| REQ-005 deterministic output directory | `repro_doctor/cli.py`; `tests/test_cli.py` output assertions | [x] |
| REQ-010 Python metadata and test-layout detection | `repro_doctor/detect.py`; `tests/test_detection.py` | [x] |
| REQ-011 Node/TypeScript metadata detection | `repro_doctor/detect.py`; `tests/test_node.py::NodeDetectionTests` | [x] |
| REQ-012 supported package-manager detection and preservation | `repro_doctor/detect.py`; pnpm, Yarn, npm tests in `tests/test_node.py` | [x] |
| REQ-013 existing test command selection | `repro_doctor/detect.py`; `tests/test_detection.py` and `tests/test_node.py` | [x] |
| REQ-014 pinned or proposed runtime | `repro_doctor/detect.py` and `repro_doctor/artifacts.py`; runtime assertions in `tests/test_detection.py` and `tests/test_node.py` | [x] |
| REQ-015 structured profile | `repro_doctor/models.py`; detector and orchestration tests | [x] |
| REQ-020 four parallel generation roles | `repro_doctor/orchestration.py`; `tests/test_orchestration.py::test_exactly_four_roles_run_concurrently_and_emit_progress` | [x] |
| REQ-021 self-contained role prompts | `repro_doctor/agents.py`; orchestration and prompt tests | [x] |
| REQ-022 structured response validation | `repro_doctor/agents.py`; malformed, unsafe, duplicate, and role-validation tests | [x] |
| REQ-023 no unrelated source changes | role allowlists in `repro_doctor/agents.py`; pipeline immutability tests | [x] |
| REQ-024 live role progress | `repro_doctor/orchestration.py`; progress assertions in `tests/test_orchestration.py` | [x] |
| REQ-025 replaceable agent integration | `AgentRunner` protocol and fake runners in `tests/test_orchestration.py` and `tests/test_verifier.py` | [x] |
| REQ-026 bounded agent timeout and failure handling | `repro_doctor/agents.py` and `repro_doctor/orchestration.py`; subprocess lifecycle tests | [x] |
| REQ-030 pinned dependency information or proposal | `repro_doctor/detect.py` and `repro_doctor/artifacts.py`; artifact tests | [x] |
| REQ-031 pinned runtime declaration | `repro_doctor/artifacts.py`; Python and Node artifact tests | [x] |
| REQ-032 working stack Dockerfile contract | `repro_doctor/artifacts.py`; Python and Node Dockerfile assertions plus verifier tests | [x] implementation / Docker environment gap |
| REQ-033 `Makefile` test target | `repro_doctor/artifacts.py`; artifact, Node mismatch, orchestration, and pipeline tests | [x] |
| REQ-034 generated README setup/run/test/Docker guidance | `repro_doctor/artifacts.py`; artifact tests | [x] |
| REQ-035 preserve package manager and lockfile | `repro_doctor/detect.py` and `repro_doctor/artifacts.py`; npm, pnpm, Yarn tests | [x] |
| REQ-036 install dependencies during image build | generated Dockerfiles in `repro_doctor/artifacts.py`; Dockerfile assertions | [x] |
| REQ-040 Docker build verification | `repro_doctor/verifier.py`; fake Docker verification tests; live gate status below | [x] implementation / Docker environment gap |
| REQ-041 run `make test` in image | `repro_doctor/verifier.py`; fake Docker command assertions | [x] implementation / Docker environment gap |
| REQ-042 verify after generation | `repro_doctor/pipeline.py`; verification pipeline tests | [x] |
| REQ-043 capture failure output | `repro_doctor/models.py`, `repro_doctor/verifier.py`, `repro_doctor/report.py`; failure report tests | [x] |
| REQ-044 route failure to focused repair role | `repro_doctor/verifier.py`; routing tests in `tests/test_verifier.py` | [x] |
| REQ-045 maximum five repair retries | `MAX_REPAIR_ATTEMPTS`; exact exhaustion test in `tests/test_verifier.py` | [x] |
| REQ-046 Docker and agent timeouts | `repro_doctor/verifier.py` and `repro_doctor/agents.py`; process cleanup tests | [x] |
| REQ-047 preserve report on verification failure | `repro_doctor/pipeline.py` and `repro_doctor/cli.py`; failure output test | [x] |
| REQ-050 applyable unified patch | `repro_doctor/patching.py`; `git apply --check` tests | [x] |
| REQ-051 Markdown report | `repro_doctor/report.py`; pipeline and example-schema tests | [x] |
| REQ-052 report stack/files/commands/result/retries | `repro_doctor/report.py`; report assertions in verifier and pipeline tests | [x] |
| REQ-053 non-zero status for unverified result | `repro_doctor/cli.py`; `tests/test_cli.py::test_verification_failure_returns_nonzero_after_outputs_exist` | [x] |

## Project quality traceability

| Requirement | Evidence | Status |
|---|---|---|
| REQ-060 pinned development dependencies | `.python-version`, `requirements-dev.lock`; `tests/test_release_readiness.py::test_required_release_files_and_pins_are_present` | [x] |
| REQ-061 project Dockerfile | `Dockerfile`; documented live build gate below | [x] implementation / Docker environment gap |
| REQ-062 single `make test` command | `Makefile`; clean-copy validation test | [x] |
| REQ-063 README setup/run/test/Docker usage | `README.md`; `tests/test_release_readiness.py::test_readme_documents_the_actual_cli_contract` | [x] |
| REQ-064 automated core tests with fakes | `tests/` fake agent and Docker runners | [x] |
| REQ-065 open-source license | `LICENSE` | [x] |
| REQ-066 focused project history | existing focused phase commits; this working tree is intentionally uncommitted for the requested review | [x] historical evidence |

## Non-goals checked

- [x] No runtime beyond Python and Node.js/TypeScript was added.
- [x] No automatic cloud deployment was added.
- [x] No automatic GitHub push or pull-request creation was added.
- [x] No arbitrary application or business-test repair was added.
- [x] Private registry credentials are neither generated nor stored.

## Environment-dependent evidence

| Command | Observed result |
|---|---|
| `docker build -t repro-doctor .` | Failed before build: `ERROR: permission denied while trying to connect to the docker API at unix:///var/run/docker.sock` |
