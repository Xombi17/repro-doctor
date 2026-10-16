# Phase 1 Context: Foundation and Python Path

## Goal

Build the first vertical slice of `repro-doctor`: accept a local repository path or GitHub URL, inspect a Python repository, create reproducibility artifacts in an isolated workspace, and emit an applyable patch plus a short report.

## Locked decisions

- Use Python 3.12 as the project development baseline.
- Use the Python standard library for runtime code where practical.
- Use `argparse` for the first CLI surface.
- Keep source repositories unchanged; all writes happen in a temporary working copy.
- Treat the input as a snapshot. A local directory may not have Git history.
- Support Python repositories first. Node support belongs to Phase 2.
- Preserve existing usable project files and lockfiles rather than replacing them.
- Generate a `Makefile` with a `test` target, a Dockerfile, dependency/runtime artifacts, and a README artifact proposal.
- Generate a unified patch and Markdown report in a caller-selected output directory.
- Keep OmniRush execution behind an interface, even though the real parallel runner belongs to Phase 3.
- Use fake/in-process generation in Phase 1 so the Python path is testable without OmniRush credentials or Docker.

## Python detection policy

Recognize common signals:

- `pyproject.toml`;
- `requirements*.txt`;
- `poetry.lock`;
- `uv.lock`;
- `Pipfile` and `Pipfile.lock`;
- `setup.py` or `setup.cfg`;
- `tests/`, `test/`, pytest configuration, or unittest files.

Return a structured profile with runtime, dependency files, lockfile, test command, package name, and confidence. Unsupported or ambiguous repositories should fail with a useful message.

## Artifact policy for the first slice

The generator should produce only reproducibility files and avoid application source edits:

- `Dockerfile`;
- `Makefile`;
- a runtime marker such as `.python-version` when absent;
- a dependency lock proposal when the repository lacks usable pinned dependency metadata;
- `README.repro-doctor.md` as the generated documentation artifact for this phase.

The final README replacement/update policy can be refined in Phase 3 when agent artifacts are introduced.

## Verification policy

Phase 1 verification is local and deterministic:

- detector tests use fixture repositories;
- patch tests apply generated diffs to a clean snapshot;
- the CLI test confirms the source repository is unchanged;
- the project `make test` command must pass.

Real Docker verification is Phase 4.

## Out of scope

- Node/TypeScript detection;
- real OmniRush subprocess calls;
- Docker execution;
- automatic dependency resolution over the network;
- GitHub push or pull-request creation.
