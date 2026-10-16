from __future__ import annotations

import configparser
import json
import os
import re
import tomllib
from pathlib import Path

from .errors import DetectionError, UnsupportedRepositoryError
from .models import NodeProfile, Profile, PythonProfile


_VERSION = re.compile(r"^(\d+\.\d+(?:\.\d+)?)$")
_EXACT_PYTHON = re.compile(r"==\s*(\d+\.\d+(?:\.\d+)?)")
_NODE_VERSION = re.compile(r"(?<!\d)(\d+(?:\.\d+){0,2})(?!\d)")
_IGNORED_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__"}
_NODE_LOCKFILES = {
    "npm": ("npm-shrinkwrap.json", "package-lock.json"),
    "pnpm": ("pnpm-lock.yaml",),
    "yarn": ("yarn.lock",),
}
_SUPPORTED_PACKAGE_MANAGERS = tuple(_NODE_LOCKFILES)
_TEST_FILE_SUFFIXES = {".cjs", ".js", ".mjs", ".ts", ".tsx"}
_PACKAGE_MANAGER = re.compile(r"^(npm|pnpm|yarn)(?:@[A-Za-z0-9][A-Za-z0-9._+:-]*)?$")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def _load_pyproject(root: Path) -> dict:
    path = root / "pyproject.toml"
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            loaded = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise DetectionError(f"invalid pyproject.toml: {exc}") from exc
    return loaded


def _load_package_json(root: Path) -> dict:
    path = root / "package.json"
    if not path.exists():
        return {}
    try:
        loaded = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        raise DetectionError(f"invalid package.json: {exc}") from exc
    if not isinstance(loaded, dict):
        raise DetectionError("package.json must contain a JSON object")
    return loaded


def _python_files(root: Path) -> list[Path]:
    matches: list[Path] = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted(
            directory for directory in directories if directory not in _IGNORED_DIRS
        )
        for filename in sorted(files):
            if filename.endswith(".py"):
                matches.append(Path(current) / filename)
    return matches


def _python_signals(root: Path) -> list[str]:
    dependency_files = _dependency_files(root)
    signals = [
        name
        for name in (
            "pyproject.toml",
            "requirements*.txt",
            "poetry.lock",
            "uv.lock",
            "Pipfile",
            "Pipfile.lock",
            "setup.py",
            "setup.cfg",
        )
        if (root / name).exists() or (name == "requirements*.txt" and dependency_files)
    ]
    test_directories = [name for name in ("tests", "test") if (root / name).is_dir()]
    if test_directories:
        signals.append(f"{test_directories[0]}/")
    if _python_files(root):
        signals.append("*.py")
    return signals


def _dependency_files(root: Path) -> tuple[str, ...]:
    names = []
    for path in sorted(root.glob("requirements*.txt")):
        names.append(path.name)
    for name in ("pyproject.toml", "Pipfile", "setup.py", "setup.cfg"):
        if (root / name).exists() and name not in names:
            names.append(name)
    return tuple(names)


def _requirements_are_pinned(path: Path) -> bool:
    entries = []
    for raw_line in _read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        entries.append(line)
    return bool(entries) and all("==" in entry for entry in entries)


def _lockfile(root: Path, dependency_files: tuple[str, ...]) -> str | None:
    for name in ("uv.lock", "poetry.lock", "Pipfile.lock", "requirements.lock"):
        if (root / name).exists():
            return name
    for name in dependency_files:
        if name.startswith("requirements") and _requirements_are_pinned(root / name):
            return name
    return None


def _package_name(root: Path, pyproject: dict) -> str | None:
    project = pyproject.get("project")
    if isinstance(project, dict) and isinstance(project.get("name"), str):
        return project["name"]
    tool = pyproject.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict) and isinstance(poetry.get("name"), str):
            return poetry["name"]
    setup_cfg = root / "setup.cfg"
    if setup_cfg.exists():
        parser = configparser.ConfigParser()
        parser.read_string(_read_text(setup_cfg))
        if parser.has_option("metadata", "name"):
            return parser.get("metadata", "name")
    setup_py = root / "setup.py"
    match = re.search(r"\bname\s*=\s*['\"]([^'\"]+)['\"]", _read_text(setup_py))
    return match.group(1) if match else None


def _runtime(root: Path, pyproject: dict) -> tuple[str, str]:
    for name in (".python-version", "runtime.txt"):
        path = root / name
        if not path.exists():
            continue
        content = _read_text(path).strip()
        value = content.splitlines()[0] if content else ""
        value = value.removeprefix("python-")
        if _VERSION.fullmatch(value):
            return value, name

    project = pyproject.get("project")
    requires_python = project.get("requires-python") if isinstance(project, dict) else None
    if isinstance(requires_python, str):
        match = _EXACT_PYTHON.search(requires_python)
        if match:
            return match.group(1), "pyproject.toml requires-python"
    return "3.12", "phase-1 default"


def _pytest_configured(root: Path, pyproject: dict, dependency_files: tuple[str, ...]) -> bool:
    tool = pyproject.get("tool")
    if isinstance(tool, dict) and isinstance(tool.get("pytest"), dict):
        return True
    for name in ("pytest.ini", "tox.ini", "setup.cfg"):
        path = root / name
        if path.exists() and "pytest" in _read_text(path).lower():
            return True
    for name in dependency_files:
        if "pytest" in _read_text(root / name).lower():
            return True
    return "pytest" in repr(pyproject).lower()


def _existing_test_command(root: Path) -> str | None:
    makefile = root / "Makefile"
    if not makefile.exists():
        return None
    in_test = False
    for raw_line in _read_text(makefile).splitlines():
        if raw_line and not raw_line[0].isspace() and raw_line.startswith("test:"):
            in_test = True
            continue
        if in_test and raw_line.startswith("\t"):
            command = raw_line.strip().removeprefix("@")
            if command:
                return command
        elif in_test and raw_line and not raw_line[0].isspace():
            in_test = False
    return None


def _test_command(root: Path, pyproject: dict, dependency_files: tuple[str, ...]) -> str:
    existing = _existing_test_command(root)
    if existing:
        return existing
    if _pytest_configured(root, pyproject, dependency_files):
        return "python -m pytest"
    for directory in ("tests", "test"):
        if (root / directory).is_dir():
            return f"python -m unittest discover -s {directory}"
    return "python -m unittest discover"


def detect_python(root: Path) -> PythonProfile:
    """Detect a supported Python repository or raise an actionable error."""

    root = root.resolve()
    if not root.is_dir():
        raise DetectionError(f"snapshot is not a directory: {root}")

    pyproject = _load_pyproject(root)
    dependency_files = _dependency_files(root)
    python_signals = _python_signals(root)

    package_json = root / "package.json"
    if package_json.exists() and python_signals:
        raise UnsupportedRepositoryError(
            "repository is ambiguous: both Python and Node metadata were found"
        )
    if package_json.exists():
        raise UnsupportedRepositoryError(
            "Node/TypeScript repositories are deferred to Phase 2"
        )
    if not python_signals:
        raise UnsupportedRepositoryError(
            "no supported Python metadata or test layout was found"
        )

    runtime, runtime_source = _runtime(root, pyproject)
    confidence = "high" if any(
        signal in python_signals
        for signal in ("pyproject.toml", "setup.py", "setup.cfg", "Pipfile")
    ) else "medium"
    return PythonProfile(
        stack="python",
        runtime=runtime,
        runtime_source=runtime_source,
        dependency_files=dependency_files,
        lockfile=_lockfile(root, dependency_files),
        test_command=_test_command(root, pyproject, dependency_files),
        package_name=_package_name(root, pyproject),
        confidence=confidence,
        signals=tuple(sorted(set(python_signals))),
    )


def _node_files(root: Path, suffixes: set[str]) -> list[Path]:
    matches: list[Path] = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted(
            directory for directory in directories if directory not in _IGNORED_DIRS
        )
        for filename in sorted(files):
            path = Path(current) / filename
            if path.suffix.lower() in suffixes:
                matches.append(path)
    return matches


def _node_test_files(root: Path) -> tuple[str, ...]:
    matches: list[str] = []
    for path in _node_files(root, _TEST_FILE_SUFFIXES):
        relative = path.relative_to(root)
        parts = relative.parts
        filename = relative.name.lower()
        stem = relative.stem.lower()
        in_test_directory = any(part.lower() in {"test", "tests", "__tests__"} for part in parts[:-1])
        named_test = stem.endswith(".test") or stem.endswith(".spec")
        if in_test_directory or named_test or filename in {"test.js", "test.ts", "test.mjs", "test.cjs"}:
            matches.append(relative.as_posix())
    return tuple(sorted(matches))


def _has_typescript(root: Path, package_json: dict) -> bool:
    if (root / "tsconfig.json").exists() or any(root.glob("tsconfig.*.json")):
        return True
    if _node_files(root, {".ts", ".tsx"}):
        return True
    for section_name in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        section = package_json.get(section_name)
        if isinstance(section, dict) and any(
            name in section for name in ("typescript", "tsx", "ts-jest", "@types/node")
        ):
            return True
    scripts = package_json.get("scripts")
    return isinstance(scripts, dict) and any(
        isinstance(command, str) and ("tsc" in command or "tsx" in command)
        for command in scripts.values()
    )


def _node_signals(
    root: Path,
    package_json: dict,
    lockfile: str | None,
    package_manager_source: str,
    test_files: tuple[str, ...],
    typescript: bool,
) -> list[str]:
    signals = ["package.json"]
    if lockfile:
        signals.append(lockfile)
    if package_manager_source == "package.json packageManager":
        signals.append("packageManager")
    if isinstance(package_json.get("engines"), dict) and package_json["engines"].get("node"):
        signals.append("engines.node")
    if (root / ".nvmrc").exists():
        signals.append(".nvmrc")
    if typescript:
        if (root / "tsconfig.json").exists():
            signals.append("tsconfig.json")
        signals.append("TypeScript source")
    if test_files:
        signals.append("test files")
    return signals


def _package_manager(
    root: Path, package_json: dict
) -> tuple[str, str, str | None, str | None]:
    explicit = package_json.get("packageManager")
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit.strip():
            raise DetectionError("package.json packageManager must be a non-empty string")
        value = explicit.strip()
        manager = value.split("@", 1)[0]
        if manager not in _SUPPORTED_PACKAGE_MANAGERS:
            supported = ", ".join(_SUPPORTED_PACKAGE_MANAGERS)
            raise UnsupportedRepositoryError(
                f"unsupported package manager '{manager}'; supported managers are {supported}"
            )
        if not _PACKAGE_MANAGER.fullmatch(value):
            raise DetectionError(f"invalid packageManager value: {explicit}")
        lockfile = next((name for name in _NODE_LOCKFILES[manager] if (root / name).exists()), None)
        return manager, "package.json packageManager", value if value != manager else None, lockfile

    lockfiles_by_manager = {
        manager: next((name for name in names if (root / name).exists()), None)
        for manager, names in _NODE_LOCKFILES.items()
    }
    managers = [manager for manager, lockfile in lockfiles_by_manager.items() if lockfile]
    if len(managers) > 1:
        details = ", ".join(
            f"{manager} ({lockfiles_by_manager[manager]})" for manager in managers
        )
        raise UnsupportedRepositoryError(
            f"repository has ambiguous package manager lockfiles: {details}; "
            "add packageManager to package.json"
        )
    if managers:
        manager = managers[0]
        return manager, f"{lockfiles_by_manager[manager]} lockfile", None, lockfiles_by_manager[manager]
    return "npm", "npm default", None, None


def _runtime_node(root: Path, package_json: dict) -> tuple[str, str]:
    nvmrc = root / ".nvmrc"
    if nvmrc.exists():
        content = _read_text(nvmrc).strip()
        value = content.splitlines()[0].strip() if content else ""
        value = value.removeprefix("v")
        if value and value not in {"node", "lts/*", "stable", "current"} and _NODE_VERSION.fullmatch(value):
            return value, ".nvmrc"
        if value:
            raise DetectionError(
                ".nvmrc must contain a concrete Node version such as 22 or 22.11.0"
            )

    engines = package_json.get("engines")
    node_engine = engines.get("node") if isinstance(engines, dict) else None
    if isinstance(node_engine, str):
        matches = _NODE_VERSION.findall(node_engine)
        if matches:
            return matches[0], "package.json engines.node"
    return "22", "phase-2 default"


def _node_package_name(package_json: dict) -> str | None:
    value = package_json.get("name")
    return value if isinstance(value, str) else None


def _scripts(package_json: dict) -> dict[str, str]:
    scripts = package_json.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {name: command for name, command in scripts.items() if isinstance(name, str) and isinstance(command, str)}


def _selected_test_script(scripts: dict[str, str]) -> str | None:
    for name in ("test", "test:ci", "ci:test"):
        if name in scripts:
            return name
    for name in sorted(scripts):
        if name.startswith("test:"):
            return name
    runner_terms = ("node --test", "jest", "vitest", "mocha", "ava", "tap")
    for name in sorted(scripts):
        if name in {"check", "verify", "ci"} and any(
            term in scripts[name].lower() for term in runner_terms
        ):
            return name
    return None


def _package_test_command(package_manager: str, script: str) -> str:
    if script == "test":
        return f"{package_manager} test"
    return f"{package_manager} run {script}"


def detect_node(root: Path) -> NodeProfile:
    """Detect a supported Node.js or TypeScript repository."""

    root = root.resolve()
    if not root.is_dir():
        raise DetectionError(f"snapshot is not a directory: {root}")
    package_path = root / "package.json"
    if not package_path.exists():
        raise UnsupportedRepositoryError("no package.json was found for a Node repository")

    python_signals = [signal for signal in _python_signals(root) if not signal.endswith("/")]
    if python_signals:
        raise UnsupportedRepositoryError(
            "repository is ambiguous: both Python and Node metadata were found"
        )
    package_json = _load_package_json(root)
    package_manager, manager_source, manager_spec, lockfile = _package_manager(root, package_json)
    dependency_files = ["package.json"]
    for names in _NODE_LOCKFILES.values():
        dependency_files.extend(name for name in names if (root / name).exists())
    test_files = _node_test_files(root)
    typescript = _has_typescript(root, package_json)
    scripts = _scripts(package_json)
    test_script = _selected_test_script(scripts)
    existing = _existing_test_command(root)
    if test_script:
        test_command = _package_test_command(package_manager, test_script)
    elif existing:
        test_command = existing
    elif test_files:
        test_command = "node --test"
    else:
        raise UnsupportedRepositoryError(
            "could not determine a Node test command; add a test package script or a clear test file"
        )
    runtime, runtime_source = _runtime_node(root, package_json)
    signals = _node_signals(
        root, package_json, lockfile, manager_source, test_files, typescript
    )
    return NodeProfile(
        stack="node",
        runtime=runtime,
        runtime_source=runtime_source,
        dependency_files=tuple(sorted(set(dependency_files))),
        lockfile=lockfile,
        package_manager=package_manager,  # type: ignore[arg-type]
        package_manager_source=manager_source,
        package_manager_spec=manager_spec,
        test_command=test_command,
        test_script=test_script,
        package_name=_node_package_name(package_json),
        typescript=typescript,
        test_files=test_files,
        confidence="high" if package_json.get("name") or test_script else "medium",
        signals=tuple(sorted(set(signals))),
    )


def detect_repository(root: Path) -> Profile:
    """Dispatch detection to the unambiguous Python or Node path."""

    root = root.resolve()
    if not root.is_dir():
        raise DetectionError(f"snapshot is not a directory: {root}")
    if (root / "package.json").exists():
        return detect_node(root)
    return detect_python(root)


def detect_profile(root: Path) -> Profile:
    """Alias for callers that want the structured repository profile."""

    return detect_repository(root)


def detect_stack(root: Path) -> Profile:
    """Alias for stack-oriented callers."""

    return detect_repository(root)
