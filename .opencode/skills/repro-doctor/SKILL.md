---
name: repro-doctor
description: Use this skill whenever a user asks to make an existing repository rebuildable, reproducible, Docker-ready, clean-Linux compatible, or ready for a Buildathon checklist. Trigger for requests involving a pinned runtime, dependency lockfile, Dockerfile, one test command, README setup instructions, `.env.example`, secret safety, absolute-path checks, or an agent skill that should run this whole workflow. It audits and repairs Python and Node.js/TypeScript repositories, runs the real checks, emits an applyable patch and report, and commits only when explicitly requested.
compatibility: Python 3.12+, Git, GNU Make; Docker and the OmniRush CLI are optional but required for their respective live verification paths.
---

# Rebuildable repository workflow

Turn the current repository into a reproducible, reviewable project that can be
checked out and rebuilt on a clean Linux machine. The CLI in this repository is
the implementation; this skill is the repeatable agent workflow around it.

## Outcome

Finish with:

- a Git repository with real commits;
- a pinned runtime declaration;
- a dependency lockfile or an explicit standard-library-only explanation;
- a Dockerfile that builds and runs the project;
- one canonical offline test command: `make test`;
- a README with exact setup, run, test, Docker, and deploy guidance;
- a committed `.env.example` containing placeholders and no secrets;
- no machine-specific absolute paths in tracked files;
- an applyable patch and Markdown report when processing a target repository.

## Safety and scope

1. Work from the repository root. Read repository instructions, `README.md`,
   `Makefile`, `Dockerfile`, runtime markers, lockfiles, `.gitignore`, and
   existing tests before editing.
2. Preserve unrelated user changes. Check `git status --short` before and after
   the work. Never reset, clean, force-push, or overwrite uncommitted work.
3. Never read or copy private credential files. `.env` is private and ignored;
   `.env.example` may contain names and safe placeholders only.
4. Keep application source behavior unchanged unless the user explicitly asks
   for an application fix. Reproducibility files and tests are in scope.
5. Never make Docker socket permissions world-writable. If Docker access is
   denied, record the live check as unverified and continue with offline checks.
6. Do not push commits or create a pull request unless explicitly requested.

## Workflow

### 1. Reconnaissance

Identify the application root and stack:

```bash
git rev-parse --show-toplevel
git status --short --branch
git log --oneline -5
python --version
git ls-files
```

Use the existing project stack. This repository supports Python and
Node.js/TypeScript targets. Do not install global packages or introduce a
starter kit.

### 2. Repair the rebuild contract

Check and repair only what is missing:

- **Git:** keep the work in a Git repository and create a conventional commit
  when the user asks to commit.
- **Runtime:** use `.python-version` for Python or `.nvmrc` for Node. Pin an
  exact version. This project baseline is Python `3.12`; Node targets use the
  detector's pinned declaration or Node 22 fallback.
- **Dependencies:** preserve an existing usable lockfile. If the project uses
  only the standard library, keep a pinned development lockfile and say that
  runtime installation is unnecessary. Never claim a lockfile is resolved if
  dependency versions are not pinned.
- **Environment:** ensure `.env.example` documents non-secret settings such as
  `OMNIRUSH_BIN=omnirush` and `DOCKER_BIN=docker`. Ignore `.env` and keep the
  example file tracked. Never place API keys, tokens, passwords, or private
  URLs in examples, tests, reports, or commits.
- **Docker:** pin the base runtime image. Install every system tool used by the
  image command, including GNU Make when the image runs `make test`. Copy the
  project, then provide a real executable `CMD` or `ENTRYPOINT`; do not replace
  a failing build with a no-op.
- **Test command:** keep one canonical `.PHONY: test` target in `Makefile` and
  make it invoke the real project test command. The command must work offline
  after dependencies are installed.
- **README:** document exact setup, run, test, Docker, and deployment behavior.
  State prerequisites and environment-dependent gaps instead of hiding them.
- **Paths:** search tracked files for machine-specific paths. Use repository
  relative paths, `/app` only inside a container, and `/tmp` only in commands
  that intentionally create disposable output.

### 3. Run the project checks

Run the smallest meaningful checks, then the full project check:

```bash
make test
python -m compileall -q repro_doctor tests
python -m repro_doctor --help
git diff --check
for prefix in /home/ /Users/ /workspace/ /mnt/; do
  git grep -nF -- "$prefix" -- ':!*.pyc' && exit 1 || true
done
```

Do not call a failed or skipped check passed. If a check is unavailable, report
the command, exit result, and reason.

### 4. Run Docker checks when available

First check daemon access:

```bash
docker info
```

If it succeeds, run:

```bash
docker build -t repro-doctor .
docker run --rm repro-doctor
docker run --rm repro-doctor make test
```

For a target repository, use the project's CLI from outside the target source
directory:

```bash
python -m repro_doctor TARGET_REPOSITORY \
  --mode local \
  --output-dir /tmp/repro-doctor-output
```

Use `--mode agent` when the `omnirush` executable and credentials are available;
it starts the four parallel roles. Use `--mode local` for deterministic,
credential-free generation. If Docker is unavailable and the user only needs a
patch, add `--skip-verification`, but label the Docker result unverified.

### 5. Report the result

Always give a checklist with `PASS`, `UNVERIFIED`, or `FAIL` for every requested
item. Include:

- files changed;
- exact commands run and their observed results;
- patch and report paths;
- Docker availability and any captured error;
- the commit hash when a commit was requested;
- the next concrete action for any unverified item.

### 6. Commit when requested

Before committing, inspect:

```bash
git status --short
git diff --check
git diff --stat
git log --oneline -10
```

Stage only intended files and use a conventional message, for example:

```bash
git add .
git commit -m "chore: make project rebuildable"
```

After the commit, rerun `make test` and report the final commit hash. Do not
claim the commit exists until `git log -1 --oneline` confirms it.

## Failure handling

- If the input repository is unsupported or ambiguous, stop with an actionable
  explanation rather than guessing.
- If OmniRush is unavailable, use local generation and say that agent mode was
  not exercised.
- If Docker is unavailable, still produce the patch/report and preserve the
  failure details. Never convert an unavailable Docker check into a pass.
- If tests fail, fix the first relevant cause, rerun the changed check, then run
  the full `make test` command.

## Final response format

Use this structure:

```markdown
## What changed
- ...

## Checklist
| Item | Status | Evidence |
|---|---|---|
| Git repository with commits | PASS | ... |

## Verification
- `make test` — ...
- `docker build ...` — ...

## Outputs
- Patch: `...`
- Report: `...`
- Commit: `...`

## Remaining gaps
- ...
```
