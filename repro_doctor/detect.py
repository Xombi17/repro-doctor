from __future__ import annotations

import configparser
import os
import re
import tomllib
from pathlib import Path

from .errors import DetectionError, UnsupportedRepositoryError
from .models import PythonProfile


_VERSION = re.compile(r"^(\d+\.\d+(?:\.\d+)?)$")
_EXACT_PYTHON = re.compile(r"==\s*(\d+\.\d+(?:\.\d+)?)")
_IGNORED_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__"}


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
    python_signals = [
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
        python_signals.append(f"{test_directories[0]}/")
    if _python_files(root):
        python_signals.append("*.py")

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
