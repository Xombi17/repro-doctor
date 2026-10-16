# Phase 3 Context: Parallel OmniRush Agent Orchestration

## Goal

Make the generation path use four concurrent OmniRush roles while preserving an injectable local runner for tests and offline development.

## Locked decisions

- Use the installed `omnirush` CLI through a subprocess adapter.
- Start exactly four generation roles per run:
  - `stack-detector`;
  - `dockerfile-writer`;
  - `test-script-writer`;
  - `readme-writer`.
- Launch all four roles concurrently against the isolated target snapshot.
- Agents return structured JSON artifacts and must not edit the target repository directly.
- The deterministic local detector remains the safety baseline. The stack-detector agent result is advisory and is validated before use.
- Writer roles receive the deterministic profile and may return only files in their assigned scope.
- Use a fake runner and in-process artifact generator in tests. Tests must not require OmniRush credentials.
- Emit role-prefixed progress events as soon as a role starts, produces output, completes, fails, or times out.
- Use `OMNIRUSH_BIN` as an executable override and a bounded per-role timeout.
- Make the real agent mode explicit in the CLI while retaining a local mode for offline operation and tests.

## Artifact ownership

| Role | Allowed artifact paths |
|---|---|
| stack-detector | none; structured profile only |
| dockerfile-writer | `Dockerfile` |
| test-script-writer | `Makefile`, dependency/runtime test support files when explicitly requested |
| readme-writer | `README.repro-doctor.md` |

The controller rejects path traversal, duplicate artifact paths, malformed JSON, and artifacts outside the role's allowlist.

## Response contract

Agents must return one JSON object:

```json
{
  "role": "dockerfile-writer",
  "artifacts": [
    {"path": "Dockerfile", "content": "...", "reason": "..."}
  ]
}
```

The stack detector returns `profile` instead of `artifacts`. Fenced JSON is accepted as a convenience, but arbitrary prose is an error.

## Out of scope

- verifier agent and Docker execution;
- automatic fix requests after verification;
- dependency resolution or lockfile generation beyond writer output;
- remote agent APIs other than the local OmniRush CLI.
