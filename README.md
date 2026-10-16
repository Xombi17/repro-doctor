# repro-doctor

`repro-doctor` creates a reviewable reproducibility patch and Markdown report
for a Python or Node.js/TypeScript repository without modifying the input
repository. It works from a local path or a public GitHub HTTPS URL.

## Requirements

- Python 3.12, pinned in [`.python-version`](.python-version).
- GNU Make for the project test command.
- Git for GitHub HTTPS inputs.
- Docker for the default generated-artifact verification and the project image.
- The `omnirush` executable for the default agent mode. Use local mode when it
  is not available.
- Optional settings are documented in [`.env.example`](.env.example); never put
  credentials in that file.

Runtime code uses only the Python standard library. Optional development
dependencies are pinned in [`requirements-dev.lock`](requirements-dev.lock).
The lockfile is for development tooling; the runtime does not need a package
installation.

## Setup

Use Python 3.12 and install the pinned optional development tooling when it is
available locally:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.lock
```

The required offline test path does not need that install:

```bash
make test
```

The dependency install can contact the Python package index. `make test` is
standard-library-only and is the supported offline project check.

If you need executable overrides, copy `.env.example` to a private `.env` file
and export the values in your shell. The `.env` file is ignored by Git.

## Run

The source argument is required. Analyze a local repository or a public GitHub
HTTPS URL and write the patch and report outside the input repository:

```bash
python -m repro_doctor ./path/to/repository --output-dir ./repro-doctor-output
python -m repro_doctor https://github.com/example/project.git --output-dir ./repro-doctor-output
```

The CLI defaults to `agent` mode, which starts the four parallel OmniRush
roles. Set `OMNIRUSH_BIN` to override the executable. For credential-free,
deterministic local generation and offline development, use:

```bash
python -m repro_doctor ./path/to/repository --mode local --skip-verification
python -m repro_doctor ./path/to/repository --mode agent --agent-timeout 60
python -m repro_doctor --help
```

The available CLI options are:

| Option | Behavior |
|---|---|
| `--output-dir PATH` | Output directory, default `repro-doctor-output`. |
| `--mode {agent,local}` | Agent orchestration or deterministic local generation; default `agent`. |
| `--agent-timeout AGENT_TIMEOUT` | Per-agent timeout in seconds; default `120.0`. |
| `--docker-timeout DOCKER_TIMEOUT` | Per-Docker-command timeout in seconds; default `300.0`. |
| `--skip-verification` | Skip generated-snapshot Docker verification. |
| `--version` | Print the package version and exit. |

## Supported stacks

The supported input contract is documented in
[SUPPORTED-REPOSITORIES.md](SUPPORTED-REPOSITORIES.md). In brief, the detector
supports Python and Node.js/TypeScript repositories. Node projects may use
npm, pnpm, or Yarn. Existing runtime declarations, package-manager metadata,
and usable lockfiles are preserved in generated artifacts.

## Verification

Unless `--skip-verification` is supplied, the CLI materializes artifacts in an
isolated snapshot, builds a local Docker image, and runs `make test` inside the
image. The generated verification commands are equivalent to:

```bash
docker build -t repro-doctor-target-TAG .
docker run --rm repro-doctor-target-TAG make test
```

The tag is generated locally for each run. Build and test commands have bounded
timeouts. A successful report records the commands and a zero retry count. A
failed report is still written and contains the failed stage, classification,
captured output, and repair attempts. Docker image publishing is not performed.

## Repair limit

Verification failures receive at most five repair attempts. Build and
dependency failures go to the Dockerfile writer; test-command failures go to
the test-script writer. Repairs are limited to reproducibility artifacts and do
not change application source or business logic.

## Test

`make test` is the single required offline project test command. It includes
unit tests for detection, isolation, artifact generation, orchestration,
verification, CLI behavior, and release readiness. The broader local release
checks are:

```bash
make test
python -m compileall -q repro_doctor tests
python -m repro_doctor --help
git diff --check
```

## Docker

Build the project CLI image and view its help command:

```bash
docker build -t repro-doctor .
docker run --rm repro-doctor
docker run --rm repro-doctor make test
```

The project Dockerfile uses Python 3.12 and the image command is the CLI help
path. It also includes GNU Make so the same image can run the project test
command. A build may need network access to pull the base image. The target
repository image created during CLI verification is separate and local.

## Agent skill

The complete rebuild workflow is also available as the repository-local
`repro-doctor` skill at `.opencode/skills/repro-doctor/SKILL.md`. It tells an
agent how to inspect the repository, repair missing reproducibility files,
run the checks, handle unavailable Docker safely, and report or commit the
result. The skill is a thin workflow layer around this CLI, so the same
commands remain reproducible outside an agent session.

The packaged skill is also downloadable from the repository:

```bash
curl -L \
  -o repro-doctor.skill \
  https://github.com/Xombi17/repro-doctor/raw/main/repro-doctor.skill
mkdir -p .opencode/skills
unzip -o repro-doctor.skill -d .opencode/skills
```

The source and package are available at:

- [Skill source](https://github.com/Xombi17/repro-doctor/tree/main/.opencode/skills/repro-doctor)
- [Download `repro-doctor.skill`](https://github.com/Xombi17/repro-doctor/raw/main/repro-doctor.skill)

## Deploy

Cloud deployment, image publishing, CI-provider configuration, GitHub pushes,
and pull-request creation are outside v1. The Docker image above is the
supported local runtime artifact; there is no deploy command in the CLI.

## Limitations

- Only Python and Node.js/TypeScript inputs are supported.
- A GitHub input must be a public repository that the local Git installation
  can clone over HTTPS.
- Private package registries work only when their credentials and configuration
  are already available to the Docker build; no credentials are created or
  copied by this project.
- The repair loop fixes generated reproducibility files and test entry points;
  it does not repair arbitrary application failures.
- Agent mode requires the local OmniRush executable and its own configured
  access. Local mode avoids that dependency.
- Docker verification requires an accessible Docker daemon and image registry
  access for any uncached base image or dependency installation.

## License

MIT. See [LICENSE](LICENSE).
