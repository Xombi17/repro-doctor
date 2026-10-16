# Supported repositories

`repro-doctor` accepts a local directory or a GitHub HTTPS URL. A local input
is copied into a temporary snapshot before detection and generation. GitHub
inputs are shallow-cloned into that workspace and Git metadata is removed
before artifacts are produced. The original repository is not modified.

## Python

A repository is eligible for the Python path when it has Python source and
recognizable project or test metadata. Detection understands:

- `pyproject.toml`, `requirements*.txt`, `setup.py`, `setup.cfg`, `Pipfile`,
  Poetry metadata, and uv metadata;
- `tests/` or `test/` layouts and Python files;
- runtime declarations in `.python-version`, `runtime.txt`, or an exact
  `requires-python` declaration in `pyproject.toml`;
- lock metadata in `uv.lock`, `poetry.lock`, `Pipfile.lock`,
  `requirements.lock`, or a fully pinned `requirements*.txt` file.

When no runtime declaration is available, the detector uses Python 3.12 as its
documented fallback. An existing `Makefile` test target is preserved. Without
one, the detector chooses pytest when it is configured, then a unittest
discovery command for a `tests/` or `test/` directory.

## Node.js and TypeScript

A repository is eligible for the Node path when it has `package.json` and a
determinable test command. The detector understands:

- JavaScript and TypeScript source, including `tsconfig*.json`;
- npm, pnpm, and Yarn;
- `package-lock.json` or `npm-shrinkwrap.json`, `pnpm-lock.yaml`, and
  `yarn.lock`;
- package-manager declarations such as `"packageManager": "pnpm@9.15.0"`;
- runtime declarations in `.nvmrc` or `engines.node`, with Node.js 22 as the
  fallback;
- `test`, `test:ci`, `ci:test`, other `test:*` scripts, and recognized test
  runner commands. A clear test file can provide the `node --test` fallback.

An explicit `packageManager` declaration wins over a lockfile signal. Multiple
different manager lockfiles without that declaration are rejected as
ambiguous. Existing package-manager choices and lockfiles are preserved.

## Dependency and lockfile policy

The generator does not silently replace an existing usable lockfile. When a
supported Node lockfile is present, the generated image uses the corresponding
frozen install command (`npm ci`, `pnpm install --frozen-lockfile`, or
`yarn install --frozen-lockfile`). When a Node lockfile is absent, the patch
documents the missing pinning work instead of inventing a lockfile. The Python
path follows the same preservation rule for recognized lock metadata.

Dependency installation happens during image build. The target build may need
network access or an already configured private registry. `make test` in the
repro-doctor project itself remains offline and standard-library-only.

## Rejected or unsupported inputs

- Repositories with neither supported Python signals nor `package.json`;
- ambiguous repositories containing both Python and Node metadata;
- Node repositories with conflicting manager lockfiles and no explicit manager;
- Node repositories without a test script, test file, or existing test target;
- runtimes other than Python and Node.js/TypeScript;
- non-GitHub URLs, private clone flows, or GitHub URLs that local Git cannot
  access.

Generated artifacts are a patch and a Markdown report. The tool does not push
changes, publish images, deploy to a cloud service, or repair application
business logic.
