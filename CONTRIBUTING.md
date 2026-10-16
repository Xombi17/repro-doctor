# Contributing

## Local setup

Use the pinned Python runtime and the optional development lockfile:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.lock
```

The runtime uses only the standard library. Do not install project dependencies
globally. `make test` does not require the optional development install and is
the offline test path.

Copy `.env.example` to a private `.env` only when you need executable overrides.
Never commit `.env` or place credentials in `.env.example`.

## Before proposing a change

Run the focused test command and the release checks that apply to the change:

```bash
make test
python -m compileall -q repro_doctor tests
python -m repro_doctor --help
git diff --check
```

If Docker is available, also run:

```bash
docker build -t repro-doctor .
```

Record daemon, registry, or permission failures instead of presenting them as
successful verification. Do not add CI-provider or cloud deployment behavior
as part of a v1 change.

## Safe local testing

- Use `--mode local --skip-verification` for deterministic, credential-free CLI
  tests.
- Put `--output-dir` outside the input repository. The CLI rejects an output
  directory inside a local source tree.
- Use temporary fixture repositories and fake agent or Docker runners for tests
  that do not need external services.
- Never put API keys, tokens, private URLs, registry credentials, or personal
  data in prompts, fixtures, reports, examples, or commits.
- Keep generated output and bytecode out of the repository; the existing
  `.gitignore` covers the normal local paths.

## Code and documentation changes

Keep changes small and preserve the standard-library runtime. Update
`SUPPORTED-REPOSITORIES.md` when detection or package-manager behavior changes.
Update the README and report examples when the CLI or report schema changes.
Add a meaningful test for user-visible behavior or a relevant boundary. Avoid
changing application behavior while working on reproducibility artifacts.

## Review checklist

- [ ] The source repository remains unchanged by the workflow.
- [ ] Existing package-manager declarations and usable lockfiles are preserved.
- [ ] Repair behavior stays within the five-attempt limit and does not edit
      application source.
- [ ] Reports contain commands, result, retry count, and captured failure data
      when applicable.
- [ ] Documentation commands match `python -m repro_doctor --help`.
- [ ] No secret or environment-specific absolute path is included.
- [ ] `.env.example` contains only safe setting names and placeholders.
