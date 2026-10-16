# Initial Project Context

This document records the bounded research completed during GSD project initialization. It is intentionally limited to the local development environment and the supplied product brief.

## Local tool availability

The workspace environment currently provides:

- Python 3.14.4;
- Node.js v24.21.0;
- Docker 29.9.0;
- GNU Make 4.4.1;
- the `omnirush` CLI.

The `omnirush` CLI supports one-shot prompts through `omnirush -p "<prompt>"`, model and sub-agent options, and yolo mode. The implementation should wrap this behavior behind an injectable runner rather than coupling core logic directly to a shell command.

## Relevant design findings

### OmniRush execution

The product requires four parallel agents and live progress. A subprocess adapter is the smallest portable integration point:

1. construct a role-specific prompt;
2. start one `omnirush -p` process per role;
3. stream stdout and stderr with a role prefix;
4. parse a structured final response;
5. terminate the process on timeout;
6. expose a fake runner to unit tests.

The prompts must prohibit secrets and unrelated source edits. Agent results should be treated as untrusted data and validated before files are written.

### Docker verification

The generated project contract is intentionally simple:

```text
docker build -t <temporary-tag> .
docker run --rm <temporary-tag> make test
```

The verifier needs separate build and test result types so a Dockerfile failure can be routed differently from a missing test command. Each command needs a timeout and captured stdout/stderr.

### Dependency reproducibility

Existing lockfiles are the strongest source of project intent and should be preserved where their package manager is supported. Repositories without a lockfile need a bounded resolution step. The implementation should make the generated lockfile policy explicit instead of claiming reproducibility when dependencies remain unconstrained.

Python and Node dependency installation belongs in the Docker build. The generated `make test` target must only execute tests and must not resolve or download dependencies.

### Patch generation

The input may not have a Git history or may contain uncommitted changes. The controller should create a temporary baseline Git repository from the input snapshot, materialize generated artifacts in a second snapshot, and use `git diff --binary` to produce an applyable patch. Ignored build directories and dependency caches should not enter the baseline.

## Risks to resolve during phase planning

1. Python lock generation can require network access and may be platform-sensitive.
2. A target repository may have multiple packages or several competing test commands.
3. A generated Dockerfile may require system packages not visible from package metadata.
4. OmniRush output formatting can vary, so structured response parsing needs a fallback error path.
5. Docker may be unavailable in a user's environment even though the CLI can still generate an unverified patch.

## Research conclusion

Proceed with a narrow vertical slice first: one Python package layout, one stable test command, one Docker verification path, and injectable boundaries. Expand detector coverage only after the first end-to-end path is passing.
