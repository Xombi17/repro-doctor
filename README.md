# repro-doctor

`repro-doctor` creates a reviewable reproducibility patch for a Python
repository without modifying the input repository.

## Requirements

- Python 3.12 (the version is pinned in `.python-version`)
- Git for GitHub HTTPS inputs

Runtime code uses only the Python standard library. Optional development
dependencies are pinned in `requirements-dev.lock`.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.lock
```

## Run

Analyze a local repository or a GitHub HTTPS URL and write the patch and
report to the selected output directory:

```bash
python -m repro_doctor ./path/to/repository --output-dir ./repro-doctor-output
python -m repro_doctor https://github.com/example/project.git --output-dir ./repro-doctor-output
```

Phase 1 supports Python repositories. GitHub input requires a repository that
is publicly cloneable by the local Git installation.

## Test

The project test command is offline and uses the standard library:

```bash
make test
```

## Docker

Build the project CLI image and view the command help:

```bash
docker build -t repro-doctor .
docker run --rm repro-doctor
```

Docker verification of generated target repositories is planned for a later
phase.

## Deploy

Cloud deployment is outside the current project scope. The Docker image above
is the supported local runtime artifact.

## License

MIT. See [LICENSE](LICENSE).
