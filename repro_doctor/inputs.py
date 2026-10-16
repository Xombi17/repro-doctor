from __future__ import annotations

import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator
from urllib.parse import urlparse
import tempfile

from .errors import InputError
from .models import Snapshot


CloneRunner = Callable[[str, Path], None]


def _is_github_https_url(value: str) -> bool:
    parsed = urlparse(value)
    segments = [segment for segment in parsed.path.strip("/").split("/") if segment]
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and parsed.hostname.lower() in {"github.com", "www.github.com"}
        and len(segments) == 2
        and not parsed.query
        and not parsed.fragment
        and not parsed.username
        and not parsed.password
    )


def _is_url(value: str) -> bool:
    return bool(urlparse(value).scheme)


def _local_source(value: str) -> Path | None:
    path = Path(value).expanduser()
    if not path.exists():
        return None
    if not path.is_dir():
        raise InputError(f"local input is not a directory: {path}")
    return path.resolve()


def _clone_github(url: str, destination: Path) -> None:
    try:
        completed = subprocess.run(
            ["git", "clone", "--depth", "1", "--", url, str(destination)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError as exc:
        raise InputError("Git is required for GitHub HTTPS inputs") from exc
    except subprocess.TimeoutExpired as exc:
        raise InputError(f"timed out while cloning {url}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise InputError(f"could not clone {url}: {detail or 'git clone failed'}")


def _copy_snapshot(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git"),
    )


def copy_snapshot(source: Path, destination: Path) -> None:
    """Copy a repository snapshot while keeping Git metadata out of patches."""

    _copy_snapshot(source, destination)


def ensure_output_is_safe(source: str, output_dir: Path) -> None:
    """Prevent a local run from writing its output back into the source."""

    local = _local_source(source)
    if local is None:
        return
    output = output_dir.expanduser().resolve()
    try:
        output.relative_to(local)
    except ValueError:
        return
    raise InputError(
        f"output directory must be outside the input repository: {output}"
    )


@contextmanager
def isolated_snapshot(
    source: str,
    *,
    clone_runner: CloneRunner | None = None,
) -> Iterator[Snapshot]:
    """Yield a temporary local or GitHub repository copy."""

    local = _local_source(source)
    if local is None and _is_url(source) and not _is_github_https_url(source):
        raise InputError("only GitHub HTTPS URLs are supported")
    if local is None and not _is_github_https_url(source):
        raise InputError(
            f"input path does not exist or is not a supported GitHub HTTPS URL: {source}"
        )

    with tempfile.TemporaryDirectory(prefix="repro-doctor-") as temporary:
        workspace = Path(temporary)
        snapshot_root = workspace / "snapshot"
        if local is not None:
            _copy_snapshot(local, snapshot_root)
            kind = "local"
        else:
            (clone_runner or _clone_github)(source, snapshot_root)
            if not snapshot_root.is_dir():
                raise InputError("Git clone did not create a repository directory")
            git_dir = snapshot_root / ".git"
            if git_dir.exists():
                shutil.rmtree(git_dir)
            kind = "github"
        yield Snapshot(root=snapshot_root, source=source, kind=kind)
