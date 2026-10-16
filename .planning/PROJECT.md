# repro-doctor

## Project purpose

`repro-doctor` is an open-source Python CLI that turns a Python or Node/TypeScript repository into a reproducible project through a reviewable patch.

Given a local repository path or GitHub URL, the CLI creates an isolated working copy, asks parallel OmniRush agents to propose the required project files, verifies the result in Docker, and emits:

- a unified patch that can be applied to the input repository;
- a short report describing the detected stack, changed files, verification result, and retry count.

The input repository is never modified directly.

## Product outcome

A user should be able to run one command against a supported repository and receive a patch that adds or repairs:

- pinned runtime and dependency information;
- a working `Dockerfile`;
- a single `make test` entry point;
- a README covering setup, run, test, and Docker usage.

The result is considered successful only when the generated Docker image builds and `make test` passes inside the container.

## Scope

### v1 included

- Python repositories;
- Node.js and TypeScript repositories;
- local filesystem paths;
- GitHub HTTPS URLs;
- npm, pnpm, and Yarn lockfile-aware workflows;
- common Python dependency and test layouts;
- parallel stack, Dockerfile, test-script, and README agents;
- live progress output;
- Docker verification;
- up to five bounded repair retries;
- deterministic patch and report generation;
- offline test execution after dependencies have been installed.

### v1 excluded

- Ruby, Go, Rust, Java, PHP, or polyglot repositories whose primary runtime is unsupported;
- deployment to a cloud provider;
- automatic publishing or pushing to GitHub;
- changing application behavior beyond reproducibility files and required package metadata;
- arbitrary CI provider configuration;
- long-running interactive agent sessions inside the target repository.

## Design principles

1. **Never mutate the source.** Work in a temporary copy and produce an explicit patch.
2. **Prefer existing project intent.** Preserve usable lockfiles, package-manager choices, test scripts, and runtime declarations.
3. **Make verification executable.** Docker build and `docker run ... make test` are the acceptance checks, not claims in a report.
4. **Bound all automation.** Agent calls, Docker commands, and retries have timeouts and hard limits.
5. **Keep the core testable offline.** The agent runner, Docker runner, and filesystem boundary are injectable in tests.
6. **Keep the output small.** Generate only the files needed to make the repository reproducible.

## Success criteria

- A clean checkout of `repro-doctor` can install its pinned dependencies and run `make test`.
- A Python fixture repository can be processed into a patch that passes Docker verification.
- A Node/TypeScript fixture repository can be processed into a patch that passes Docker verification.
- Four generation roles run concurrently and expose live progress.
- A verifier runs only after the generation roles complete.
- A failed verification can trigger a focused repair and succeed on a later attempt.
- A persistently failing verification stops after five retries and reports the failure without hanging.
- The original input repository remains unchanged.
- The generated patch is applicable with `git apply` to the original snapshot.

## Working assumptions

- The implementation will use Python 3.12 as its development baseline unless repository evidence requires another supported interpreter.
- The runtime implementation will favor the standard library; development dependencies will be pinned in a lockfile.
- OmniRush will be integrated through a subprocess adapter around the installed `omnirush` CLI, with a fake adapter for tests.
- Docker is a required verifier prerequisite for real runs, but unit tests will not require Docker.
- A local MIT license will make the project open-source-ready. Publishing requires a user-provided GitHub remote and will not happen automatically.

## Current state

Version 1 is implemented and archived. The CLI supports isolated Python and
Node.js/TypeScript analysis, four-role OmniRush generation, Docker verification,
bounded repair, applyable patches, reports, clean-copy validation, and release
documentation. The offline suite passes 42 tests, including a follow-up
portability check for Python 3.14's colored argparse help.

The Docker build gate is explicitly unverified in the development workspace
because `/var/run/docker.sock` is not accessible to the current user. Re-run
the documented project and target-fixture Docker checks on a Docker-capable
machine before treating the release as Docker-verified.

## Next milestone goals

- Start a fresh requirements and roadmap cycle with `/gsd-new-milestone`.
- Re-run project and generated-target Docker verification in an environment with
  an accessible daemon and registry access.
- Consider future support for additional repository ecosystems only after a
  new scope decision; v1 remains limited to Python and Node.js/TypeScript.
